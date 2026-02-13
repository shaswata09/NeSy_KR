#!/usr/bin/env python3
"""
GQA paginated API server.

Loads GQA scene graphs and balanced questions, then serves paginated
slices cast into the Augmenter UI dataset-template format.
Also serves local GQA images over HTTP.

Endpoints:
  GET /api/gqa?offset=0&limit=50  ->  { total, offset, limit, items: [...] }
  GET /api/gqa/health             ->  { status: "ok", total: N }
  GET /images/<id>.jpg            ->  serves the image file

Usage:
  python gqa_server.py                  # all 85,638 images (train+val), port 8101
  python gqa_server.py --split val      # val only (10,696 images, faster startup)
  python gqa_server.py --port 9001      # custom port
  python gqa_server.py --host 127.0.0.1 # localhost only
"""

import argparse
import json
import mimetypes
import sys
import time
from http.server import HTTPServer, BaseHTTPRequestHandler
from pathlib import Path
from urllib.parse import parse_qs, urlparse

# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------
SCRIPT_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = SCRIPT_DIR.parents[3]  # ui/src/data/gqa -> project root
DATA_DIR = PROJECT_ROOT / "data" / "gqa"
IMAGES_DIR = DATA_DIR / "allImages" / "images"

# ---------------------------------------------------------------------------
# Caps
# ---------------------------------------------------------------------------
MAX_NODES = 30
MAX_LINKS = 30
MAX_ATTRIBUTES = 40
MAX_QAS = 20
MAX_LIMIT = 200  # safety cap per request

# ---------------------------------------------------------------------------
# Global state (populated on startup)
# ---------------------------------------------------------------------------
scene_graphs = None       # {image_id: {width, height, objects: {oid: {...}}}}
questions_by_image = None  # {image_id: [{question, answer, ...}, ...]}
image_ids = None           # sorted list of image IDs with scene graphs


def _load_scene_graphs(splits):
    """Load and merge scene graphs from one or more splits."""
    merged = {}
    for split in splits:
        sg_path = DATA_DIR / "sceneGraphs" / f"{split}_sceneGraphs.json"
        print(f"  Loading scene graphs from {sg_path.name}...")
        with open(sg_path) as f:
            data = json.load(f)
        print(f"    {len(data):,} images")
        merged.update(data)
    return merged


def _load_questions(splits):
    """Load and index balanced questions from one or more splits."""
    by_image = {}
    for split in splits:
        q_path = DATA_DIR / "questions1.2" / f"{split}_balanced_questions.json"
        print(f"  Loading questions from {q_path.name}...")
        with open(q_path) as f:
            raw_qs = json.load(f)
        print(f"    {len(raw_qs):,} questions")
        for qid, q in raw_qs.items():
            img_id = q["imageId"]
            if img_id not in by_image:
                by_image[img_id] = []
            by_image[img_id].append({"qid": qid, **q})
        del raw_qs
    return by_image


def load_all(split="all"):
    """Load GQA scene graphs and balanced questions.

    split: 'val', 'train', or 'all' (both train + val, default).
    """
    global scene_graphs, questions_by_image, image_ids

    splits = ["train", "val"] if split == "all" else [split]

    scene_graphs = _load_scene_graphs(splits)
    print(f"  Total scene graphs: {len(scene_graphs):,}")

    questions_by_image = _load_questions(splits)

    # Only include images that have scene graphs and exist on disk
    image_ids = sorted(
        iid for iid in scene_graphs
        if (IMAGES_DIR / f"{iid}.jpg").exists()
    )
    print(f"  Images with scene graphs + local file: {len(image_ids):,}")


# ---------------------------------------------------------------------------
# Casting logic
# ---------------------------------------------------------------------------
def make_name_from_objects(objects_dict, max_words=3):
    """Build a short name from the most prominent objects."""
    names = []
    for oid in list(objects_dict.keys())[:max_words]:
        label = objects_dict[oid]["name"].capitalize()
        if label not in names:
            names.append(label)
    return " & ".join(names) if names else "Scene"


def categorize_attribute(attr_str):
    """Map a GQA attribute string to a semantic category."""
    a = attr_str.lower()
    if a in (
        "white", "black", "red", "blue", "green", "yellow", "brown",
        "gray", "grey", "orange", "pink", "purple", "beige", "silver",
        "gold", "tan",
    ):
        return "color"
    if a in (
        "wooden", "metal", "glass", "plastic", "stone", "concrete",
        "brick", "fabric", "leather", "rubber",
    ):
        return "material"
    if a in ("large", "small", "tall", "short", "big", "tiny", "long"):
        return "size"
    if a in ("round", "square", "rectangular", "circular", "flat"):
        return "shape"
    return "property"


def cast_image(image_id, server_base):
    """Cast a GQA image into the UI dataset-template format."""
    sg = scene_graphs[image_id]
    objects = sg["objects"]

    # Nodes (capped)
    nodes = []
    node_ids = set()
    for oid in list(objects.keys())[:MAX_NODES]:
        obj = objects[oid]
        nodes.append({
            "id": oid,
            "label": obj["name"].capitalize(),
            "bbox": {"x": obj["x"], "y": obj["y"], "w": obj["w"], "h": obj["h"]},
        })
        node_ids.add(oid)

    # Links from relations (capped)
    links = []
    for oid in node_ids:
        for rel in objects[oid].get("relations", []):
            target = rel["object"]
            if target in node_ids:
                links.append({
                    "source": oid,
                    "target": target,
                    "label": rel["name"],
                })
                if len(links) >= MAX_LINKS:
                    break
        if len(links) >= MAX_LINKS:
            break

    # Attributes
    attributes = []
    for oid in node_ids:
        for attr_str in objects[oid].get("attributes", []):
            attributes.append({
                "entityId": oid,
                "attribute": categorize_attribute(attr_str),
                "value": attr_str,
            })
            if len(attributes) >= MAX_ATTRIBUTES:
                break
        if len(attributes) >= MAX_ATTRIBUTES:
            break

    # QA pairs
    qas = []
    for q in (questions_by_image.get(image_id) or [])[:MAX_QAS]:
        qas.append({
            "id": f"qa_{q['qid']}",
            "question": q["question"],
            "answer": q.get("fullAnswer") or q.get("answer", ""),
        })

    return {
        "id": f"gqa_{image_id}",
        "name": make_name_from_objects(objects),
        "imageUrl": f"{server_base}/images/{image_id}.jpg",
        "width": sg["width"],
        "height": sg["height"],
        "metadata": {
            "source": "GQA",
            "imageId": image_id,
            "numObjects": len(objects),
            "numRelations": sum(len(objects[o].get("relations", [])) for o in objects),
            "numQAs": len(questions_by_image.get(image_id, [])),
        },
        "groundTruth": {
            "nodes": nodes,
            "links": links,
            "attributes": attributes,
            "qas": qas,
        },
        "prediction": None,
    }


# ---------------------------------------------------------------------------
# HTTP handler
# ---------------------------------------------------------------------------
class GQAHandler(BaseHTTPRequestHandler):
    def _get_base_url(self):
        """Derive the public base URL from the incoming request Host header."""
        host = self.headers.get("Host", f"localhost:{self.server.server_port}")
        return f"http://{host}"

    def do_GET(self):
        parsed = urlparse(self.path)

        if parsed.path == "/api/gqa/health":
            self._json({"status": "ok", "total": len(image_ids)})

        elif parsed.path == "/api/gqa":
            params = parse_qs(parsed.query)
            offset = max(0, int(params.get("offset", ["0"])[0]))
            limit = min(int(params.get("limit", ["50"])[0]), MAX_LIMIT)
            offset = min(offset, len(image_ids))

            t0 = time.time()
            base_url = self._get_base_url()
            page_ids = image_ids[offset : offset + limit]
            items = [cast_image(iid, base_url) for iid in page_ids]
            elapsed = time.time() - t0

            self.log_message(
                "page offset=%d limit=%d returned=%d (%.1fs)",
                offset, limit, len(items), elapsed,
            )
            self._json({
                "total": len(image_ids),
                "offset": offset,
                "limit": limit,
                "items": items,
            })

        elif parsed.path.startswith("/images/"):
            # Serve local image files
            filename = parsed.path.split("/")[-1]
            filepath = IMAGES_DIR / filename
            if filepath.exists() and filepath.is_file():
                content_type = mimetypes.guess_type(str(filepath))[0] or "image/jpeg"
                data = filepath.read_bytes()
                self.send_response(200)
                self.send_header("Content-Type", content_type)
                self.send_header("Content-Length", len(data))
                self.send_header("Cache-Control", "public, max-age=86400")
                self._cors()
                self.end_headers()
                self.wfile.write(data)
            else:
                self._json({"error": "Image not found"}, status=404)

        else:
            self._json({"error": "Not found"}, status=404)

    def do_OPTIONS(self):
        self.send_response(204)
        self._cors()
        self.end_headers()

    def _cors(self):
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")

    def _json(self, data, status=200):
        body = json.dumps(data, ensure_ascii=False).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", len(body))
        self._cors()
        self.end_headers()
        self.wfile.write(body)


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------
def _get_local_ip():
    """Best-effort detection of the machine's LAN IP."""
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
    parser = argparse.ArgumentParser(description="GQA paginated API server")
    parser.add_argument("--host", default="0.0.0.0", help="Bind address (default: 0.0.0.0)")
    parser.add_argument("--port", type=int, default=8101, help="Port (default: 8101)")
    parser.add_argument("--split", default="all", choices=["val", "train", "all"], help="Data split (default: all = train+val)")
    args = parser.parse_args()

    print(f"Loading GQA {args.split} split...")
    load_all(args.split)

    lan_ip = _get_local_ip()

    print(f"\nReady. {len(image_ids):,} images available.")
    print(f"Serving on:")
    print(f"  Local:   http://localhost:{args.port}")
    print(f"  Network: http://{lan_ip}:{args.port}\n")
    print("Endpoints:")
    print(f"  GET /api/gqa?offset=0&limit=50")
    print(f"  GET /api/gqa/health")
    print(f"  GET /images/<id>.jpg\n")

    server = HTTPServer((args.host, args.port), GQAHandler)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nShutting down.")
        server.server_close()


if __name__ == "__main__":
    main()
