"""Visual Genome dataset adapter."""

from pathlib import Path
from typing import Any

from api.adapter_base import DatasetAdapter
from api.shared import (
    MAX_ATTRIBUTES,
    MAX_LINKS,
    MAX_NODES,
    MAX_QAS,
    categorize_attribute,
)

PROJECT_ROOT = Path(__file__).resolve().parents[2]
CACHE_DIR = str(PROJECT_ROOT / "data" / "visual_genome" / "hf_cache")

VERSION = "1.2.0"
CONFIGS = {
    "objects": f"objects_v{VERSION}",
    "relationships": f"relationships_v{VERSION}",
    "attributes": f"attributes_v{VERSION}",
    "question_answers": f"question_answers_v{VERSION}",
    "region_descriptions": f"region_descriptions_v{VERSION}",
}


def _make_name(objects, max_words=3):
    """Build a short name from VG object names list."""
    names = []
    for obj in objects[:max_words]:
        label = obj["names"][0] if obj["names"] else None
        if label and label.capitalize() not in names:
            names.append(label.capitalize())
    return " & ".join(names) if names else "Scene"


class VGAdapter(DatasetAdapter):
    def __init__(self):
        self._subsets = None
        self._id_maps = None
        self._common_ids = None

    @property
    def name(self) -> str:
        return "vg"

    @property
    def display_name(self) -> str:
        return "Visual Genome"

    @property
    def splits(self) -> list[str]:
        return ["train"]

    @property
    def has_local_images(self) -> bool:
        return False

    @property
    def total(self) -> int:
        return len(self._common_ids) if self._common_ids else 0

    def load(self, split: str = "all") -> None:
        from datasets import load_dataset

        self._subsets = {}
        self._id_maps = {}
        for ds_name, config in CONFIGS.items():
            print(f"  [VG] Loading {ds_name}...")
            try:
                ds = load_dataset(
                    "visual_genome",
                    config,
                    split="train",
                    cache_dir=CACHE_DIR,
                    trust_remote_code=True,
                )
                ds = ds.remove_columns("image")
                self._subsets[ds_name] = ds

                print(f"    Building index ({len(ds):,} rows)...")
                id_map = {}
                for i in range(len(ds)):
                    id_map[ds[i]["image_id"]] = i
                self._id_maps[ds_name] = id_map
            except Exception as e:
                print(f"    WARNING: Skipping {ds_name}: {e}")

        if not self._id_maps:
            raise RuntimeError("No VG subsets could be loaded")

        # Common IDs = intersection of all successfully loaded subsets
        id_sets = [set(m.keys()) for m in self._id_maps.values()]
        cids = id_sets[0]
        for s in id_sets[1:]:
            cids &= s
        self._common_ids = sorted(cids)
        print(f"  [VG] Loaded subsets: {list(self._subsets.keys())}")
        print(f"  [VG] Common images: {len(self._common_ids):,}")

    def get_image_ids(self) -> list:
        return self._common_ids or []

    def get_image_ids_for_split(self, split: str = "all") -> list:
        if split in ["all", "train"]:
            return self.get_image_ids()
        return []

    def cast(self, index: int, server_base_url: str) -> dict[str, Any]:
        image_id = self._common_ids[index]
        return self.cast_item(image_id, server_base_url)

    def _get_row(self, subset_name: str, image_id: int):
        """Get a row from a subset, or None if the subset is not loaded."""
        if subset_name not in self._subsets:
            return None
        return self._subsets[subset_name][self._id_maps[subset_name][image_id]]

    def cast_item(self, image_id: int, server_base_url: str) -> dict[str, Any]:
        obj_row = self._get_row("objects", image_id)
        rel_row = self._get_row("relationships", image_id)
        attr_row = self._get_row("attributes", image_id)
        qa_row = self._get_row("question_answers", image_id)
        reg_row = self._get_row("region_descriptions", image_id)

        # Nodes
        nodes = []
        node_ids = set()
        if obj_row:
            for obj in obj_row["objects"][:MAX_NODES]:
                oid = str(obj["object_id"])
                label = obj["names"][0].capitalize() if obj["names"] else f"Object {oid}"
                nodes.append(
                    {
                        "id": oid,
                        "label": label,
                        "bbox": {
                            "x": obj["x"],
                            "y": obj["y"],
                            "w": obj["w"],
                            "h": obj["h"],
                        },
                    }
                )
                node_ids.add(oid)

        # Links
        links = []
        if rel_row:
            for rel in rel_row["relationships"][:MAX_LINKS]:
                src = str(rel["subject"]["object_id"])
                tgt = str(rel["object"]["object_id"])
                if src in node_ids and tgt in node_ids:
                    links.append({"source": src, "target": tgt, "label": rel["predicate"]})

        # Attributes
        attributes = []
        if attr_row:
            for attr in attr_row["attributes"][:MAX_ATTRIBUTES]:
                eid = str(attr["object_id"])
                if eid not in node_ids:
                    continue
                for a in attr.get("attributes") or []:
                    attributes.append(
                        {
                            "entityId": eid,
                            "attribute": categorize_attribute(a),
                            "value": a,
                        }
                    )

        # QA pairs
        qas = []
        if qa_row:
            for qa in qa_row["qas"][:MAX_QAS]:
                qas.append(
                    {
                        "id": f"qa_{qa['qa_id']}",
                        "question": qa["question"],
                        "answer": qa["answer"],
                    }
                )

        # Use whichever row is available for image metadata
        meta_row = obj_row or reg_row or rel_row or attr_row or qa_row
        image_url = (obj_row or {}).get("url", "")
        width = meta_row["width"] if meta_row else 0
        height = meta_row["height"] if meta_row else 0

        return {
            "id": f"vg_{image_id}",
            "name": _make_name(obj_row["objects"] if obj_row else []),
            "imageUrl": image_url,
            "width": width,
            "height": height,
            "metadata": {
                "source": "Visual Genome",
                "imageId": image_id,
                "numObjects": len(obj_row["objects"]) if obj_row else 0,
                "numRelations": len(rel_row["relationships"]) if rel_row else 0,
                "numRegions": len(reg_row["regions"]) if reg_row else 0,
                "numQAs": len(qa_row["qas"]) if qa_row else 0,
            },
            "groundTruth": {
                "nodes": nodes,
                "links": links,
                "attributes": attributes,
                "qas": qas,
            },
            "prediction": None,
        }
