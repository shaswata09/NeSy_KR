"""Shared constants and utilities for dataset adapters."""

MAX_NODES = 30
MAX_LINKS = 30
MAX_ATTRIBUTES = 40
MAX_QAS = 20
MAX_LIMIT = 200  # safety cap per request


def categorize_attribute(attr_str: str) -> str:
    """Map an attribute string to a semantic category."""
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
