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

        cids = set(self._id_maps["objects"].keys())
        for name in self._id_maps:
            cids &= set(self._id_maps[name].keys())
        self._common_ids = sorted(cids)
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

    def cast_item(self, image_id: int, server_base_url: str) -> dict[str, Any]:
        obj_row = self._subsets["objects"][self._id_maps["objects"][image_id]]
        rel_row = self._subsets["relationships"][
            self._id_maps["relationships"][image_id]
        ]
        attr_row = self._subsets["attributes"][self._id_maps["attributes"][image_id]]
        qa_row = self._subsets["question_answers"][
            self._id_maps["question_answers"][image_id]
        ]
        reg_row = self._subsets["region_descriptions"][
            self._id_maps["region_descriptions"][image_id]
        ]

        # Nodes
        nodes = []
        node_ids = set()
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
        for qa in qa_row["qas"][:MAX_QAS]:
            qas.append(
                {
                    "id": f"qa_{qa['qa_id']}",
                    "question": qa["question"],
                    "answer": qa["answer"],
                }
            )

        return {
            "id": f"vg_{image_id}",
            "name": _make_name(obj_row["objects"]),
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
