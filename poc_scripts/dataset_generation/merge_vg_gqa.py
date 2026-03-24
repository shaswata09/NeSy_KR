"""Merge Visual Genome + GQA into a unified JSONL dataset.

Train split: ALL of Visual Genome + GQA train
Val split:   GQA val only

Output format follows the NeSy_KR dataset-template schema, extended to
preserve ALL annotations from both sources (synsets, region descriptions,
full QA metadata, etc.).

Usage:
    python poc_scripts/dataset_generation/merge_vg_gqa.py
    python poc_scripts/dataset_generation/merge_vg_gqa.py --output-dir data/merged
    python poc_scripts/dataset_generation/merge_vg_gqa.py --format json   # single JSON array (large!)
"""

import argparse
import json
import sys
import time
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(PROJECT_ROOT))

# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------
GQA_DIR = PROJECT_ROOT / "data" / "gqa"
GQA_IMAGES_DIR = GQA_DIR / "allImages" / "images"
GQA_SG_DIR = GQA_DIR / "sceneGraphs"
GQA_Q_DIR = GQA_DIR / "questions1.2"

VG_CACHE_DIR = str(PROJECT_ROOT / "data" / "visual_genome" / "hf_cache")

from api.shared import categorize_attribute  # noqa: E402

# ---------------------------------------------------------------------------
# GQA conversion
# ---------------------------------------------------------------------------


def convert_gqa_image(image_id, sg, questions, split):
    """Convert a single GQA image to the unified schema."""
    objects = sg["objects"]

    # Nodes
    nodes = []
    for oid, obj in objects.items():
        nodes.append({
            "id": oid,
            "label": obj["name"],
            "bbox": {"x": obj["x"], "y": obj["y"], "w": obj["w"], "h": obj["h"]},
        })

    # Links
    links = []
    obj_id_set = set(objects.keys())
    for oid, obj in objects.items():
        for rel in obj.get("relations", []):
            target = rel["object"]
            if target in obj_id_set:
                links.append({
                    "source": oid,
                    "target": target,
                    "label": rel["name"],
                })

    # Attributes
    attributes = []
    for oid, obj in objects.items():
        for attr_str in obj.get("attributes", []):
            attributes.append({
                "entityId": oid,
                "attribute": categorize_attribute(attr_str),
                "value": attr_str,
            })

    # QA pairs
    qas = []
    for q in questions:
        qa_entry = {
            "id": f"qa_{q['qid']}",
            "question": q["question"],
            "answer": q.get("answer", ""),
            "fullAnswer": q.get("fullAnswer"),
        }
        if "types" in q:
            qa_entry["types"] = q["types"]
        if "semantic" in q:
            qa_entry["semanticProgram"] = q["semantic"]
        if "entailed" in q:
            qa_entry["entailed"] = q["entailed"]
        if "equivalent" in q:
            qa_entry["equivalent"] = q["equivalent"]
        if "isBalanced" in q:
            qa_entry["isBalanced"] = q["isBalanced"]
        qas.append(qa_entry)

    image_path = str(GQA_IMAGES_DIR / f"{image_id}.jpg")

    return {
        "id": f"gqa_{image_id}",
        "name": _make_name_gqa(objects),
        "image_id": str(image_id),
        "image_path": image_path,
        "width": sg["width"],
        "height": sg["height"],
        "metadata": {
            "source": "gqa",
            "split": split,
        },
        "groundTruth": {
            "nodes": nodes,
            "links": links,
            "attributes": attributes,
            "qas": qas,
            "regions": [],
        },
        "prediction": None,
    }


def _make_name_gqa(objects_dict, max_words=3):
    names = []
    for oid in list(objects_dict.keys())[:max_words]:
        label = objects_dict[oid]["name"].capitalize()
        if label not in names:
            names.append(label)
    return " & ".join(names) if names else "Scene"


# ---------------------------------------------------------------------------
# VG conversion
# ---------------------------------------------------------------------------


def convert_vg_image(image_id, subsets, id_maps):
    """Convert a single VG image to the unified schema."""

    def get_row(subset_name):
        if subset_name not in subsets or image_id not in id_maps.get(subset_name, {}):
            return None
        return subsets[subset_name][id_maps[subset_name][image_id]]

    obj_row = get_row("objects")
    rel_row = get_row("relationships")
    attr_row = get_row("attributes")
    qa_row = get_row("question_answers")
    reg_row = get_row("region_descriptions")

    # Use any available row for image metadata
    meta_row = obj_row or reg_row or rel_row or attr_row or qa_row
    if meta_row is None:
        return None

    # Nodes
    nodes = []
    node_id_set = set()
    if obj_row:
        for obj in obj_row["objects"]:
            oid = str(obj["object_id"])
            node = {
                "id": oid,
                "label": obj["names"][0].capitalize() if obj["names"] else f"Object {oid}",
                "names": obj.get("names", []),
                "synsets": obj.get("synsets", []),
                "bbox": {"x": obj["x"], "y": obj["y"], "w": obj["w"], "h": obj["h"]},
            }
            if "merged_object_ids" in obj:
                node["mergedObjectIds"] = obj["merged_object_ids"]
            nodes.append(node)
            node_id_set.add(oid)

    # Links
    links = []
    if rel_row:
        for rel in rel_row["relationships"]:
            src = str(rel["subject"]["object_id"])
            tgt = str(rel["object"]["object_id"])
            link = {
                "source": src,
                "target": tgt,
                "label": rel["predicate"],
            }
            if rel.get("synsets"):
                link["synsets"] = rel["synsets"]
            # Preserve subject/object details for relationship entries
            link["subjectName"] = (
                rel["subject"]["names"][0] if rel["subject"].get("names") else None
            )
            link["objectName"] = (
                rel["object"]["names"][0] if rel["object"].get("names") else None
            )
            links.append(link)

    # Attributes
    attributes = []
    if attr_row:
        for attr in attr_row["attributes"]:
            eid = str(attr["object_id"])
            for a in attr.get("attributes") or []:
                attributes.append({
                    "entityId": eid,
                    "attribute": categorize_attribute(a),
                    "value": a,
                })

    # QA pairs
    qas = []
    if qa_row:
        for qa in qa_row["qas"]:
            qa_entry = {
                "id": f"qa_{qa['qa_id']}",
                "question": qa["question"],
                "answer": qa["answer"],
            }
            # Preserve grounding objects
            if qa.get("q_objects"):
                qa_entry["questionObjects"] = [
                    {
                        "objectId": str(o["object_id"]),
                        "names": o.get("names", []),
                        "synsets": o.get("synsets", []),
                        "bbox": {"x": o["x"], "y": o["y"], "w": o["w"], "h": o["h"]},
                    }
                    for o in qa["q_objects"]
                ]
            if qa.get("a_objects"):
                qa_entry["answerObjects"] = [
                    {
                        "objectId": str(o["object_id"]),
                        "names": o.get("names", []),
                        "synsets": o.get("synsets", []),
                        "bbox": {"x": o["x"], "y": o["y"], "w": o["w"], "h": o["h"]},
                    }
                    for o in qa["a_objects"]
                ]
            qas.append(qa_entry)

    # Region descriptions
    regions = []
    if reg_row:
        for reg in reg_row["regions"]:
            regions.append({
                "id": str(reg["region_id"]),
                "phrase": reg["phrase"],
                "bbox": {
                    "x": reg["x"], "y": reg["y"],
                    "w": reg["width"], "h": reg["height"],
                },
            })

    # Metadata
    metadata = {
        "source": "vg",
        "split": "train",
    }
    if meta_row.get("coco_id"):
        metadata["cocoId"] = meta_row["coco_id"]
    if meta_row.get("flickr_id"):
        metadata["flickrId"] = meta_row["flickr_id"]

    return {
        "id": f"vg_{image_id}",
        "name": _make_name_vg(obj_row["objects"] if obj_row else []),
        "image_id": str(image_id),
        "image_url": meta_row.get("url", ""),
        "width": meta_row["width"],
        "height": meta_row["height"],
        "metadata": metadata,
        "groundTruth": {
            "nodes": nodes,
            "links": links,
            "attributes": attributes,
            "qas": qas,
            "regions": regions,
        },
        "prediction": None,
    }


def _make_name_vg(objects, max_words=3):
    names = []
    for obj in objects[:max_words]:
        label = obj["names"][0].capitalize() if obj.get("names") else None
        if label and label not in names:
            names.append(label)
    return " & ".join(names) if names else "Scene"


# ---------------------------------------------------------------------------
# Writers
# ---------------------------------------------------------------------------


class JSONLWriter:
    """Write one JSON object per line."""

    def __init__(self, path):
        self.path = path
        self.fh = open(path, "w")
        self.count = 0

    def write(self, entry):
        self.fh.write(json.dumps(entry, ensure_ascii=False) + "\n")
        self.count += 1

    def close(self):
        self.fh.close()


class JSONArrayWriter:
    """Write as a single JSON array (streams with manual comma handling)."""

    def __init__(self, path):
        self.path = path
        self.fh = open(path, "w")
        self.fh.write("[\n")
        self.count = 0

    def write(self, entry):
        if self.count > 0:
            self.fh.write(",\n")
        json.dump(entry, self.fh, ensure_ascii=False)
        self.count += 1

    def close(self):
        self.fh.write("\n]\n")
        self.fh.close()


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------


def load_vg_subsets():
    """Load all VG subsets from HuggingFace cache."""
    from datasets import load_dataset

    VERSION = "1.2.0"
    CONFIGS = {
        "objects": f"objects_v{VERSION}",
        "relationships": f"relationships_v{VERSION}",
        "attributes": f"attributes_v{VERSION}",
        "question_answers": f"question_answers_v{VERSION}",
        "region_descriptions": f"region_descriptions_v{VERSION}",
    }

    subsets = {}
    id_maps = {}
    for ds_name, config in CONFIGS.items():
        print(f"  [VG] Loading {ds_name}...", flush=True)
        try:
            ds = load_dataset(
                "visual_genome", config, split="train",
                cache_dir=VG_CACHE_DIR, trust_remote_code=True,
            )
            ds = ds.remove_columns("image")
            subsets[ds_name] = ds

            print(f"    Building index ({len(ds):,} rows)...", flush=True)
            id_map = {}
            for i in range(len(ds)):
                id_map[ds[i]["image_id"]] = i
            id_maps[ds_name] = id_map
        except Exception as e:
            print(f"    WARNING: Skipping {ds_name}: {e}", flush=True)

    if not id_maps:
        print("  ERROR: No VG subsets loaded.", flush=True)
        return {}, {}, []

    # Common image IDs across all loaded subsets
    id_sets = [set(m.keys()) for m in id_maps.values()]
    common_ids = id_sets[0]
    for s in id_sets[1:]:
        common_ids &= s
    common_ids = sorted(common_ids)

    print(f"  [VG] Loaded subsets: {list(subsets.keys())}")
    print(f"  [VG] Common images: {len(common_ids):,}")
    return subsets, id_maps, common_ids


def load_gqa_split(split):
    """Load GQA scene graphs + questions for a split. Returns (scene_graphs, questions_by_image, image_ids)."""
    # Scene graphs
    sg_path = GQA_SG_DIR / f"{split}_sceneGraphs.json"
    print(f"  [GQA] Loading {sg_path.name}...", flush=True)
    with open(sg_path) as f:
        scene_graphs = json.load(f)
    print(f"    {len(scene_graphs):,} images", flush=True)

    # Filter to images with local file
    image_ids = sorted(
        iid for iid in scene_graphs if (GQA_IMAGES_DIR / f"{iid}.jpg").exists()
    )
    print(f"    {len(image_ids):,} with local image", flush=True)

    # Questions
    q_path = GQA_Q_DIR / f"{split}_balanced_questions.json"
    print(f"  [GQA] Loading {q_path.name}...", flush=True)
    with open(q_path) as f:
        raw_qs = json.load(f)
    print(f"    {len(raw_qs):,} questions", flush=True)

    questions_by_image = {}
    for qid, q in raw_qs.items():
        img_id = q["imageId"]
        if img_id not in questions_by_image:
            questions_by_image[img_id] = []
        questions_by_image[img_id].append({"qid": qid, **q})
    del raw_qs

    return scene_graphs, questions_by_image, image_ids


def main():
    parser = argparse.ArgumentParser(description="Merge VG + GQA into unified dataset")
    parser.add_argument(
        "--output-dir", type=str,
        default=str(PROJECT_ROOT / "data" / "merged"),
        help="Output directory for merged files",
    )
    parser.add_argument(
        "--format", choices=["jsonl", "json"], default="jsonl",
        help="Output format: jsonl (default, streaming) or json (single array)",
    )
    args = parser.parse_args()

    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    ext = "jsonl" if args.format == "jsonl" else "json"
    WriterClass = JSONLWriter if args.format == "jsonl" else JSONArrayWriter

    t0 = time.time()

    # ── Load all data ─────────────────────────────────────────────────────
    print("\n═══ Loading Visual Genome ═══", flush=True)
    vg_subsets, vg_id_maps, vg_image_ids = load_vg_subsets()

    print("\n═══ Loading GQA (train) ═══", flush=True)
    gqa_train_sg, gqa_train_qs, gqa_train_ids = load_gqa_split("train")

    print("\n═══ Loading GQA (val) ═══", flush=True)
    gqa_val_sg, gqa_val_qs, gqa_val_ids = load_gqa_split("val")

    # ── Write train split ─────────────────────────────────────────────────
    train_path = output_dir / f"train.{ext}"
    print(f"\n═══ Writing train split → {train_path} ═══", flush=True)

    train_writer = WriterClass(train_path)
    stats = {"vg": 0, "gqa_train": 0, "errors": 0}

    # VG entries
    for i, image_id in enumerate(vg_image_ids):
        try:
            entry = convert_vg_image(image_id, vg_subsets, vg_id_maps)
            if entry:
                train_writer.write(entry)
                stats["vg"] += 1
        except Exception as e:
            stats["errors"] += 1
            if stats["errors"] <= 5:
                print(f"    WARNING: VG image {image_id}: {e}", flush=True)

        if (i + 1) % 10000 == 0:
            print(f"    VG: {i + 1:,}/{len(vg_image_ids):,}", flush=True)

    print(f"  VG done: {stats['vg']:,} entries", flush=True)

    # GQA train entries
    for i, image_id in enumerate(gqa_train_ids):
        try:
            entry = convert_gqa_image(
                image_id, gqa_train_sg[image_id],
                gqa_train_qs.get(image_id, []), "train",
            )
            train_writer.write(entry)
            stats["gqa_train"] += 1
        except Exception as e:
            stats["errors"] += 1
            if stats["errors"] <= 5:
                print(f"    WARNING: GQA train image {image_id}: {e}", flush=True)

        if (i + 1) % 10000 == 0:
            print(f"    GQA train: {i + 1:,}/{len(gqa_train_ids):,}", flush=True)

    train_writer.close()
    print(f"  GQA train done: {stats['gqa_train']:,} entries", flush=True)
    print(f"  Train total: {train_writer.count:,} entries", flush=True)

    # ── Free train data from memory ───────────────────────────────────────
    del vg_subsets, vg_id_maps, vg_image_ids
    del gqa_train_sg, gqa_train_qs, gqa_train_ids

    # ── Write val split ───────────────────────────────────────────────────
    val_path = output_dir / f"val.{ext}"
    print(f"\n═══ Writing val split → {val_path} ═══", flush=True)

    val_writer = WriterClass(val_path)
    val_errors = 0

    for i, image_id in enumerate(gqa_val_ids):
        try:
            entry = convert_gqa_image(
                image_id, gqa_val_sg[image_id],
                gqa_val_qs.get(image_id, []), "val",
            )
            val_writer.write(entry)
        except Exception as e:
            val_errors += 1
            if val_errors <= 5:
                print(f"    WARNING: GQA val image {image_id}: {e}", flush=True)

        if (i + 1) % 5000 == 0:
            print(f"    GQA val: {i + 1:,}/{len(gqa_val_ids):,}", flush=True)

    val_writer.close()
    print(f"  Val total: {val_writer.count:,} entries", flush=True)

    # ── Summary ───────────────────────────────────────────────────────────
    elapsed = time.time() - t0
    train_size = train_path.stat().st_size / (1024 ** 3)
    val_size = val_path.stat().st_size / (1024 ** 3)

    print(f"\n{'═' * 60}")
    print(f"  DONE in {elapsed:.0f}s")
    print(f"{'═' * 60}")
    print(f"  Train: {train_writer.count:,} entries ({train_size:.2f} GB)")
    print(f"    - Visual Genome:  {stats['vg']:,}")
    print(f"    - GQA train:      {stats['gqa_train']:,}")
    print(f"  Val:   {val_writer.count:,} entries ({val_size:.2f} GB)")
    print(f"    - GQA val:        {val_writer.count:,}")
    if stats["errors"] + val_errors > 0:
        print(f"  Errors: {stats['errors'] + val_errors}")
    print(f"\n  Output: {output_dir}")
    print(f"    {train_path.name}")
    print(f"    {val_path.name}")


if __name__ == "__main__":
    main()
