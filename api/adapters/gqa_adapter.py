"""GQA dataset adapter."""

import json
from pathlib import Path
from typing import Any

from api.adapter_base import DatasetAdapter
from api.shared import MAX_NODES, MAX_LINKS, MAX_ATTRIBUTES, MAX_QAS, categorize_attribute

PROJECT_ROOT = Path(__file__).resolve().parents[2]
DATA_DIR = PROJECT_ROOT / "data" / "gqa"
IMAGES_DIR = DATA_DIR / "allImages" / "images"


def _make_name(objects_dict, max_words=3):
    """Build a short name from GQA object names."""
    names = []
    for oid in list(objects_dict.keys())[:max_words]:
        label = objects_dict[oid]["name"].capitalize()
        if label not in names:
            names.append(label)
    return " & ".join(names) if names else "Scene"


class GQAAdapter(DatasetAdapter):
    def __init__(self):
        self._scene_graphs = None
        self._questions_by_image = None
        self._image_ids = None

    @property
    def name(self) -> str:
        return "gqa"

    @property
    def display_name(self) -> str:
        return "GQA"

    @property
    def splits(self) -> list[str]:
        return ["train", "val"]

    @property
    def has_local_images(self) -> bool:
        return True

    @property
    def images_dir(self) -> Path:
        return IMAGES_DIR

    @property
    def total(self) -> int:
        return len(self._image_ids) if self._image_ids else 0

    def load(self, split: str = "all") -> None:
        splits = ["train", "val"] if split == "all" else [split]

        # Scene graphs
        self._scene_graphs = {}
        for s in splits:
            sg_path = DATA_DIR / "sceneGraphs" / f"{s}_sceneGraphs.json"
            print(f"  [GQA] Loading scene graphs from {sg_path.name}...")
            with open(sg_path) as f:
                data = json.load(f)
            print(f"    {len(data):,} images")
            self._scene_graphs.update(data)

        # Questions
        self._questions_by_image = {}
        for s in splits:
            q_path = DATA_DIR / "questions1.2" / f"{s}_balanced_questions.json"
            print(f"  [GQA] Loading questions from {q_path.name}...")
            with open(q_path) as f:
                raw_qs = json.load(f)
            print(f"    {len(raw_qs):,} questions")
            for qid, q in raw_qs.items():
                img_id = q["imageId"]
                if img_id not in self._questions_by_image:
                    self._questions_by_image[img_id] = []
                self._questions_by_image[img_id].append({"qid": qid, **q})
            del raw_qs

        # Filter to images with scene graphs + local file
        self._image_ids = sorted(
            iid for iid in self._scene_graphs
            if (IMAGES_DIR / f"{iid}.jpg").exists()
        )
        print(f"  [GQA] Images with scene graphs + local file: {len(self._image_ids):,}")

    def get_image_ids(self) -> list:
        return self._image_ids or []

    def cast(self, index: int, server_base_url: str) -> dict[str, Any]:
        image_id = self._image_ids[index]
        sg = self._scene_graphs[image_id]
        objects = sg["objects"]

        # Nodes
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

        # Links
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
        for q in (self._questions_by_image.get(image_id) or [])[:MAX_QAS]:
            qas.append({
                "id": f"qa_{q['qid']}",
                "question": q["question"],
                "answer": q.get("fullAnswer") or q.get("answer", ""),
            })

        return {
            "id": f"gqa_{image_id}",
            "name": _make_name(objects),
            "imageUrl": f"{server_base_url}/api/datasets/gqa/images/{image_id}.jpg",
            "width": sg["width"],
            "height": sg["height"],
            "metadata": {
                "source": "GQA",
                "imageId": image_id,
                "numObjects": len(objects),
                "numRelations": sum(len(objects[o].get("relations", [])) for o in objects),
                "numQAs": len(self._questions_by_image.get(image_id, [])),
            },
            "groundTruth": {
                "nodes": nodes,
                "links": links,
                "attributes": attributes,
                "qas": qas,
            },
            "prediction": None,
        }
