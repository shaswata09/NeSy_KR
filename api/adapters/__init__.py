"""
Adapter registry.

To add a new dataset, create a new adapter module implementing DatasetAdapter,
import it here, and add its class to ADAPTER_REGISTRY.
"""

from api.adapters.vg_adapter import VGAdapter
from api.adapters.gqa_adapter import GQAAdapter

ADAPTER_REGISTRY: list[type] = [
    VGAdapter,
    GQAAdapter,
]
