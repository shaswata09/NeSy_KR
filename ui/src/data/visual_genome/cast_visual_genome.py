#!/usr/bin/env python3
"""
Cast Visual Genome HuggingFace dataset into the UI sampleData.json format.

Reads the cached VG arrow files from data/visual_genome/hf_cache,
joins all 5 subsets by image_id, and outputs a JSON array matching
the dataset-template.json schema used by the Augmenter UI.

Usage:
    python cast_visual_genome.py                    # default: 50 images
    python cast_visual_genome.py --num-images 100
    python cast_visual_genome.py --image-ids 1 2 3  # specific images
"""

import argparse
import json
import random
import sys
from pathlib import Path

# Resolve paths relative to this script
SCRIPT_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = SCRIPT_DIR.parents[3]  # ui/src/data/visual_genome -> project root
CACHE_DIR = str(PROJECT_ROOT / "data" / "visual_genome" / "hf_cache")
OUTPUT_PATH = SCRIPT_DIR / "visualGenomeData.json"

VERSION = "1.2.0"
CONFIGS = {
    "objects": f"objects_v{VERSION}",
    "relationships": f"relationships_v{VERSION}",
    "attributes": f"attributes_v{VERSION}",
    "question_answers": f"question_answers_v{VERSION}",
    "region_descriptions": f"region_descriptions_v{VERSION}",
}

# Cap annotations per image to keep the JSON manageable for the UI
MAX_NODES = 30
MAX_LINKS = 30
MAX_ATTRIBUTES = 40
MAX_QAS = 20


def load_subsets():
    """Load all VG subsets and build image_id -> row index maps."""
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
        ds = ds.remove_columns("image")  # skip image decoding
        subsets[name] = ds

        id_map = {}
        for i in range(len(ds)):
            id_map[ds[i]["image_id"]] = i
        id_maps[name] = id_map

    # Common image IDs across all subsets
    common_ids = set(id_maps["objects"].keys())
    for name in id_maps:
        common_ids &= set(id_maps[name].keys())

    return subsets, id_maps, sorted(common_ids)


def make_name_from_objects(objects, max_words=3):
    """Generate a human-readable name from the top objects in the image."""
    names = []
    for obj in objects[:max_words]:
        label = obj["names"][0] if obj["names"] else None
        if label and label.capitalize() not in names:
            names.append(label.capitalize())
    return " & ".join(names) if names else "Scene"


def cast_image(image_id, subsets, id_maps):
    """Convert a single image's annotations into the UI format."""
    # --- Fetch rows from each subset ---
    obj_row = subsets["objects"][id_maps["objects"][image_id]]
    rel_row = subsets["relationships"][id_maps["relationships"][image_id]]
    attr_row = subsets["attributes"][id_maps["attributes"][image_id]]
    qa_row = subsets["question_answers"][id_maps["question_answers"][image_id]]
    reg_row = subsets["region_descriptions"][id_maps["region_descriptions"][image_id]]

    # --- Nodes (from objects) ---
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

    # --- Links (from relationships) ---
    links = []
    for rel in rel_row["relationships"][:MAX_LINKS]:
        src = str(rel["subject"]["object_id"])
        tgt = str(rel["object"]["object_id"])
        # Only include links whose endpoints exist in our node set
        if src in node_ids and tgt in node_ids:
            links.append({
                "source": src,
                "target": tgt,
                "label": rel["predicate"],
            })

    # --- Attributes ---
    attributes = []
    for attr in attr_row["attributes"][:MAX_ATTRIBUTES]:
        eid = str(attr["object_id"])
        if eid not in node_ids:
            continue
        attr_list = attr.get("attributes") or []
        obj_name = attr["names"][0] if attr["names"] else "unknown"
        for a in attr_list:
            # Infer attribute key from common patterns
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
            attributes.append({
                "entityId": eid,
                "attribute": attr_key,
                "value": a,
            })

    # --- QA pairs ---
    qas = []
    for qa in qa_row["qas"][:MAX_QAS]:
        qas.append({
            "id": f"qa_{qa['qa_id']}",
            "question": qa["question"],
            "answer": qa["answer"],
        })

    # --- Assemble entry ---
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
        # prediction is left null — to be populated by model inference
        "prediction": None,
    }


def main():
    parser = argparse.ArgumentParser(
        description="Cast Visual Genome data into UI JSON format"
    )
    parser.add_argument(
        "--num-images", type=int, default=50,
        help="Number of random images to include (default: 50)",
    )
    parser.add_argument(
        "--image-ids", type=int, nargs="+", default=None,
        help="Specific image IDs to include (overrides --num-images)",
    )
    parser.add_argument(
        "--seed", type=int, default=42,
        help="Random seed for image sampling (default: 42)",
    )
    parser.add_argument(
        "--output", type=str, default=str(OUTPUT_PATH),
        help=f"Output JSON path (default: {OUTPUT_PATH})",
    )
    args = parser.parse_args()

    random.seed(args.seed)

    print("Loading Visual Genome subsets...")
    subsets, id_maps, common_ids = load_subsets()
    print(f"  {len(common_ids):,} images available across all subsets\n")

    # Select images
    if args.image_ids:
        selected = []
        for iid in args.image_ids:
            if iid in set(common_ids):
                selected.append(iid)
            else:
                print(f"  WARNING: image_id {iid} not found in all subsets, skipping")
        selected.sort()
    else:
        n = min(args.num_images, len(common_ids))
        selected = sorted(random.sample(common_ids, n))

    print(f"Casting {len(selected)} images...")
    entries = []
    for i, image_id in enumerate(selected):
        entry = cast_image(image_id, subsets, id_maps)
        entries.append(entry)
        if (i + 1) % 10 == 0 or i == len(selected) - 1:
            print(f"  [{i + 1}/{len(selected)}] done")

    output_path = Path(args.output)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with open(output_path, "w") as f:
        json.dump(entries, f, indent=2, ensure_ascii=False)

    size_mb = output_path.stat().st_size / (1024 * 1024)
    print(f"\nWrote {len(entries)} entries to {output_path} ({size_mb:.1f} MB)")


if __name__ == "__main__":
    main()
