"""Shared fixtures for API tests.

Uses mock adapters so tests run without real data files.
"""

import tempfile
from pathlib import Path
from typing import Any

import pytest

from api.adapter_base import DatasetAdapter
from api.server import create_app


# ---------------------------------------------------------------------------
# Mock adapters
# ---------------------------------------------------------------------------

class MockVGAdapter(DatasetAdapter):
    """Simulates Visual Genome (no local images)."""

    def __init__(self):
        self._items = []

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
        return len(self._items)

    def load(self, split: str = "all") -> None:
        self._items = [
            {
                "id": f"vg_{i}",
                "name": f"Scene {i}",
                "imageUrl": f"http://example.com/img_{i}.jpg",
                "width": 800,
                "height": 600,
                "metadata": {"source": "Visual Genome", "imageId": i},
                "groundTruth": {
                    "nodes": [{"id": "1", "label": "Cat", "bbox": {"x": 0, "y": 0, "w": 50, "h": 50}}],
                    "links": [],
                    "attributes": [],
                    "qas": [],
                },
                "prediction": None,
            }
            for i in range(5)
        ]

    def get_image_ids(self) -> list:
        return list(range(len(self._items)))

    def cast(self, index: int, server_base_url: str) -> dict[str, Any]:
        return self._items[index]


class MockGQAAdapter(DatasetAdapter):
    """Simulates GQA (with local images)."""

    def __init__(self):
        self._items = []
        self._images_dir = None

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
        return self._images_dir

    @property
    def total(self) -> int:
        return len(self._items)

    def load(self, split: str = "all") -> None:
        self._images_dir = Path(tempfile.mkdtemp())
        # Create a dummy image file
        (self._images_dir / "1000.jpg").write_bytes(b"\xff\xd8\xff\xe0fake-jpeg")

        self._items = [
            {
                "id": f"gqa_{i}",
                "name": f"GQA Scene {i}",
                "imageUrl": f"PLACEHOLDER/api/datasets/gqa/images/{i}.jpg",
                "width": 640,
                "height": 480,
                "metadata": {"source": "GQA", "imageId": str(i)},
                "groundTruth": {
                    "nodes": [{"id": "10", "label": "Dog", "bbox": {"x": 10, "y": 10, "w": 100, "h": 100}}],
                    "links": [{"source": "10", "target": "10", "label": "self"}],
                    "attributes": [{"entityId": "10", "attribute": "color", "value": "brown"}],
                    "qas": [{"id": "qa_1", "question": "What?", "answer": "Dog"}],
                },
                "prediction": None,
            }
            for i in range(3)
        ]

    def get_image_ids(self) -> list:
        return list(range(len(self._items)))

    def cast(self, index: int, server_base_url: str) -> dict[str, Any]:
        item = dict(self._items[index])
        item["imageUrl"] = item["imageUrl"].replace("PLACEHOLDER", server_base_url)
        return item


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture()
def mock_adapters():
    """Return instantiated + loaded mock adapters."""
    vg = MockVGAdapter()
    vg.load("all")
    gqa = MockGQAAdapter()
    gqa.load("all")
    return [type(vg), type(gqa)], {"vg": vg, "gqa": gqa}


@pytest.fixture()
def app(mock_adapters):
    """Create a Flask app with pre-loaded mock adapters."""
    adapter_classes, loaded = mock_adapters
    flask_app = create_app(adapters_to_load=adapter_classes)
    # Replace with our pre-loaded instances
    flask_app.config["ADAPTERS"] = loaded
    flask_app.config["TESTING"] = True
    return flask_app


@pytest.fixture()
def client(app):
    """Flask test client."""
    return app.test_client()
