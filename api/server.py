#!/usr/bin/env python3
"""
Unified Dataset API Server.

Serves all registered datasets from a single Flask application.
Adapters are discovered from api/adapters/ADAPTER_REGISTRY.

Endpoints:
  GET /api/health                              -> server + per-dataset status
  GET /api/datasets                            -> list available datasets
  GET /api/datasets/<name>?offset=0&limit=50   -> paginated items
  GET /api/datasets/<name>/images/<filename>   -> serve local images

Usage:
  python -m api.server                      # all datasets, port 8200
  python -m api.server --split val          # val split only (faster)
  python -m api.server --port 9000          # custom port
  python -m api.server --host 127.0.0.1     # localhost only
"""

import argparse
import mimetypes
import time

from flask import Flask, jsonify, request, send_file, abort
from flask_cors import CORS

from api.shared import MAX_LIMIT
from api.adapters import ADAPTER_REGISTRY


def create_app(adapters_to_load=None, split="all"):
    """Flask application factory.

    Args:
        adapters_to_load: list of adapter classes. Defaults to ADAPTER_REGISTRY.
        split: data split passed to each adapter's load().
    """
    app = Flask(__name__)
    CORS(app)

    loaded_adapters = {}

    if adapters_to_load is None:
        adapters_to_load = ADAPTER_REGISTRY

    for AdapterClass in adapters_to_load:
        adapter = AdapterClass()
        try:
            adapter.load(split)
            loaded_adapters[adapter.name] = adapter
        except Exception as e:
            print(f"  WARNING: Failed to load {adapter.name}: {e}")

    app.config["ADAPTERS"] = loaded_adapters

    # ------------------------------------------------------------------
    # Routes
    # ------------------------------------------------------------------

    @app.route("/api/health")
    def health():
        datasets_status = {}
        for name, adapter in loaded_adapters.items():
            datasets_status[name] = {
                "display_name": adapter.display_name,
                "total": adapter.total,
                "status": "ok" if adapter.total > 0 else "empty",
            }
        return jsonify({
            "status": "ok",
            "datasets": datasets_status,
        })

    @app.route("/api/datasets")
    def list_datasets():
        result = []
        for name, adapter in loaded_adapters.items():
            result.append({
                "name": name,
                "displayName": adapter.display_name,
                "total": adapter.total,
                "splits": adapter.splits,
                "hasLocalImages": adapter.has_local_images,
            })
        return jsonify(result)

    @app.route("/api/datasets/<name>")
    def get_dataset_page(name):
        adapter = loaded_adapters.get(name)
        if adapter is None:
            return jsonify({"error": f"Dataset '{name}' not found"}), 404

        offset = max(0, request.args.get("offset", 0, type=int))
        limit = min(request.args.get("limit", 50, type=int), MAX_LIMIT)
        offset = min(offset, adapter.total)

        t0 = time.time()
        server_base = request.host_url.rstrip("/")
        items = []
        for i in range(offset, min(offset + limit, adapter.total)):
            items.append(adapter.cast(i, server_base))
        elapsed = time.time() - t0

        app.logger.info(
            "[%s] offset=%d limit=%d returned=%d (%.1fs)",
            name, offset, limit, len(items), elapsed,
        )

        return jsonify({
            "total": adapter.total,
            "offset": offset,
            "limit": limit,
            "items": items,
        })

    @app.route("/api/datasets/<name>/images/<filename>")
    def serve_image(name, filename):
        adapter = loaded_adapters.get(name)
        if adapter is None:
            return jsonify({"error": f"Dataset '{name}' not found"}), 404

        if not adapter.has_local_images or adapter.images_dir is None:
            return jsonify({"error": f"Dataset '{name}' does not serve local images"}), 404

        filepath = adapter.images_dir / filename
        if not filepath.exists() or not filepath.is_file():
            return jsonify({"error": "Image not found"}), 404

        # Path traversal protection
        try:
            filepath.resolve().relative_to(adapter.images_dir.resolve())
        except ValueError:
            abort(403)

        content_type = mimetypes.guess_type(str(filepath))[0] or "image/jpeg"
        response = send_file(filepath, mimetype=content_type)
        response.headers["Cache-Control"] = "public, max-age=86400"
        return response

    return app


# ------------------------------------------------------------------
# CLI entry point
# ------------------------------------------------------------------
def _get_local_ip():
    import socket
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("8.8.8.8", 80))
        ip = s.getsockname()[0]
        s.close()
        return ip
    except Exception:
        return "127.0.0.1"


def main():
    parser = argparse.ArgumentParser(description="Unified Dataset API Server")
    parser.add_argument("--host", default="0.0.0.0", help="Bind address (default: 0.0.0.0)")
    parser.add_argument("--port", type=int, default=8200, help="Port (default: 8200)")
    parser.add_argument("--split", default="all", choices=["val", "train", "all"],
                        help="Data split (default: all)")
    args = parser.parse_args()

    print("Loading datasets...")
    app = create_app(split=args.split)

    adapters = app.config["ADAPTERS"]
    total_items = sum(a.total for a in adapters.values())
    lan_ip = _get_local_ip()

    print(f"\nReady. {len(adapters)} dataset(s), {total_items:,} total items.")
    print(f"Serving on:")
    print(f"  Local:   http://localhost:{args.port}")
    print(f"  Network: http://{lan_ip}:{args.port}\n")
    print("Endpoints:")
    print(f"  GET /api/health")
    print(f"  GET /api/datasets")
    for name in adapters:
        print(f"  GET /api/datasets/{name}?offset=0&limit=50")
    print()

    app.run(host=args.host, port=args.port, debug=False)


if __name__ == "__main__":
    main()
