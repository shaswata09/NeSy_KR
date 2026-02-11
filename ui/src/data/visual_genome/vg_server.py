#!/usr/bin/env python3
"""
Visual Genome paginated API server.

Loads all 5 VG HuggingFace subsets on startup, then serves paginated
slices cast into the Augmenter UI dataset-template format.

Endpoints:
  GET /api/vg?offset=0&limit=50  ->  { total, offset, limit, items: [...] }
  GET /api/vg/health             ->  { status: "ok", total: N }

Usage:
  python vg_server.py                  # default port 8100
  python vg_server.py --port 9000      # custom port
"""

import argparse
import json
import sys
import time
from http.server import HTTPServer, BaseHTTPRequestHandler
from pathlib import Path
from urllib.parse import parse_qs, urlparse

# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------
SCRIPT_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = SCRIPT_DIR.parents[3]  # ui/src/data/visual_genome -> project root
CACHE_DIR = str(PROJECT_ROOT / "data" / "visual_genome" / "hf_cache")

# ---------------------------------------------------------------------------
# Dataset config
# ---------------------------------------------------------------------------
VERSION = "1.2.0"
CONFIGS = {
    "objects": f"objects_v{VERSION}",
    "relationships": f"relationships_v{VERSION}",
    "attributes": f"attributes_v{VERSION}",
    "question_answers": f"question_answers_v{VERSION}",
    "region_descriptions": f"region_descriptions_v{VERSION}",
}

MAX_NODES = 30
MAX_LINKS = 30
MAX_ATTRIBUTES = 40
MAX_QAS = 20
MAX_LIMIT = 200  # safety cap per request

# ---------------------------------------------------------------------------
# Global state (populated on startup)
# ---------------------------------------------------------------------------
subsets = None
id_maps = None
common_ids = None  # sorted list of image_ids present in all subsets


def load_all():
    """Load all VG subsets, build id maps, compute common image IDs."""
    global subsets, id_maps, common_ids
    from datasets import load_dataset

    subsets = {}
    id_maps = {}
    for name, config in CONFIGS.items():
        print(f"  Loading {name}...")
        ds = load_dataset(
            "visual_genome",
            config,
            split="train",
            cache_dir=CACHE_DIR,
            trust_remote_code=True,
        )
        ds = ds.remove_columns("image")
        subsets[name] = ds

        print(f"    Building index ({len(ds):,} rows)...")
        id_map = {}
        for i in range(len(ds)):
            id_map[ds[i]["image_id"]] = i
        id_maps[name] = id_map

    cids = set(id_maps["objects"].keys())
    for name in id_maps:
        cids &= set(id_maps[name].keys())
    common_ids = sorted(cids)
    print(f"  Common images across all subsets: {len(common_ids):,}")


# ---------------------------------------------------------------------------
# Casting logic (duplicated from cast_visual_genome.py for independence)
# ---------------------------------------------------------------------------
def make_name_from_objects(objects, max_words=3):
    names = []
    for obj in objects[:max_words]:
        label = obj["names"][0] if obj["names"] else None
        if label and label.capitalize() not in names:
            names.append(label.capitalize())
    return " & ".join(names) if names else "Scene"


def cast_image(image_id):
    obj_row = subsets["objects"][id_maps["objects"][image_id]]
    rel_row = subsets["relationships"][id_maps["relationships"][image_id]]
    attr_row = subsets["attributes"][id_maps["attributes"][image_id]]
    qa_row = subsets["question_answers"][id_maps["question_answers"][image_id]]
    reg_row = subsets["region_descriptions"][id_maps["region_descriptions"][image_id]]

    # Nodes
    nodes = []
    node_ids = set()
    for obj in obj_row["objects"][:MAX_NODES]:
        oid = str(obj["object_id"])
        label = obj["names"][0].capitalize() if obj["names"] else f"Object {oid}"
        nodes.append({
            "id": oid,
            "label": label,
            "bbox": {"x": obj["x"], "y": obj["y"], "w": obj["w"], "h": obj["h"]},
        })
        node_ids.add(oid)

    # Links
    links = []
    for rel in rel_row["relationships"][:MAX_LINKS]:
        src = str(rel["subject"]["object_id"])
        tgt = str(rel["object"]["object_id"])
        if src in node_ids and tgt in node_ids:
            links.append({"source": src, "target": tgt, "label": rel["predicate"]})

    # Attributes
    attributes = []
    for attr in attr_row["attributes"][:MAX_ATTRIBUTES]:
        eid = str(attr["object_id"])
        if eid not in node_ids:
            continue
        for a in (attr.get("attributes") or []):
            a_lower = a.lower()
            if a_lower in (
                "white", "black", "red", "blue", "green", "yellow", "brown",
                "gray", "grey", "orange", "pink", "purple", "beige", "silver",
                "gold", "tan",
            ):
                attr_key = "color"
            elif a_lower in (
                "wooden", "metal", "glass", "plastic", "stone", "concrete",
                "brick", "fabric", "leather", "rubber",
            ):
                attr_key = "material"
            elif a_lower in ("large", "small", "tall", "short", "big", "tiny", "long"):
                attr_key = "size"
            elif a_lower in ("round", "square", "rectangular", "circular", "flat"):
                attr_key = "shape"
            else:
                attr_key = "property"
            attributes.append({"entityId": eid, "attribute": attr_key, "value": a})

    # QA pairs
    qas = []
    for qa in qa_row["qas"][:MAX_QAS]:
        qas.append({
            "id": f"qa_{qa['qa_id']}",
            "question": qa["question"],
            "answer": qa["answer"],
        })

    return {
        "id": f"vg_{image_id}",
        "name": make_name_from_objects(obj_row["objects"]),
        "imageUrl": obj_row["url"],
        "width": obj_row["width"],
        "height": obj_row["height"],
        "metadata": {
            "source": "Visual Genome",
            "imageId": image_id,
            "numObjects": len(obj_row["objects"]),
            "numRelations": len(rel_row["relationships"]),
            "numRegions": len(reg_row["regions"]),
            "numQAs": len(qa_row["qas"]),
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
class VGHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        parsed = urlparse(self.path)

        if parsed.path == "/api/vg/health":
            self._json({"status": "ok", "total": len(common_ids)})

        elif parsed.path == "/api/vg":
            params = parse_qs(parsed.query)
            offset = max(0, int(params.get("offset", ["0"])[0]))
            limit = min(int(params.get("limit", ["50"])[0]), MAX_LIMIT)
            offset = min(offset, len(common_ids))

            t0 = time.time()
            page_ids = common_ids[offset : offset + limit]
            items = [cast_image(iid) for iid in page_ids]
            elapsed = time.time() - t0

            self.log_message(
                "page offset=%d limit=%d returned=%d (%.1fs)",
                offset, limit, len(items), elapsed,
            )
            self._json({
                "total": len(common_ids),
                "offset": offset,
                "limit": limit,
                "items": items,
            })
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
def main():
    parser = argparse.ArgumentParser(description="Visual Genome paginated API server")
    parser.add_argument("--port", type=int, default=8100, help="Port (default: 8100)")
    args = parser.parse_args()

    print("Loading Visual Genome subsets...")
    load_all()
    print(f"\nReady. {len(common_ids):,} images available.")
    print(f"Serving on http://localhost:{args.port}\n")
    print("Endpoints:")
    print(f"  GET http://localhost:{args.port}/api/vg?offset=0&limit=50")
    print(f"  GET http://localhost:{args.port}/api/vg/health\n")

    server = HTTPServer(("", args.port), VGHandler)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nShutting down.")
        server.server_close()


if __name__ == "__main__":
    main()
