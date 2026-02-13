"""Abstract base class for dataset adapters."""

from abc import ABC, abstractmethod
from pathlib import Path
from typing import Any, Optional


class DatasetAdapter(ABC):
    """Interface that every dataset plugin must implement.

    To add a new dataset:
    1. Create a new module in api/adapters/ implementing this class
    2. Add the class to ADAPTER_REGISTRY in api/adapters/__init__.py
    """

    @property
    @abstractmethod
    def name(self) -> str:
        """Unique short name used in URL paths, e.g. 'vg', 'gqa'."""
        ...

    @property
    @abstractmethod
    def display_name(self) -> str:
        """Human-readable label, e.g. 'Visual Genome'."""
        ...

    @property
    @abstractmethod
    def splits(self) -> list[str]:
        """Available data splits, e.g. ['train'], ['train', 'val']."""
        ...

    @property
    @abstractmethod
    def has_local_images(self) -> bool:
        """True if this dataset serves images from local filesystem."""
        ...

    @property
    def images_dir(self) -> Optional[Path]:
        """Filesystem path to local images. Required if has_local_images is True."""
        return None

    @abstractmethod
    def load(self, split: str = "all") -> None:
        """Load dataset into memory. Called once at server startup."""
        ...

    @property
    @abstractmethod
    def total(self) -> int:
        """Total number of available items after load()."""
        ...

    @abstractmethod
    def cast(self, index: int, server_base_url: str) -> dict[str, Any]:
        """Cast item at positional index into the dataset-template format.

        server_base_url is provided so adapters with local images can build
        absolute URLs like '{server_base_url}/api/datasets/gqa/images/123.jpg'.
        """
        ...

    @abstractmethod
    def get_image_ids(self) -> list:
        """Return the ordered list of image IDs."""
        ...
