"""Tests for the DatasetAdapter ABC interface."""

import pytest

from api.adapter_base import DatasetAdapter


def test_cannot_instantiate_abc():
    """DatasetAdapter should not be instantiable directly."""
    with pytest.raises(TypeError):
        DatasetAdapter()


def test_incomplete_subclass_raises_type_error():
    """A subclass that doesn't implement all abstract methods should fail."""
    class BadAdapter(DatasetAdapter):
        @property
        def name(self):
            return "bad"

    with pytest.raises(TypeError):
        BadAdapter()


def test_mock_adapters_are_valid_subclasses(mock_adapters):
    """Mock adapters from conftest should be proper DatasetAdapter subclasses."""
    _, loaded = mock_adapters
    for adapter in loaded.values():
        assert isinstance(adapter, DatasetAdapter)


def test_adapter_required_properties(mock_adapters):
    """Each adapter should expose the required properties after load()."""
    _, loaded = mock_adapters
    for adapter in loaded.values():
        assert isinstance(adapter.name, str)
        assert isinstance(adapter.display_name, str)
        assert isinstance(adapter.splits, list)
        assert isinstance(adapter.has_local_images, bool)
        assert isinstance(adapter.total, int)
        assert adapter.total > 0


def test_adapter_cast_returns_dict(mock_adapters):
    """cast() should return a dict with the expected top-level keys."""
    _, loaded = mock_adapters
    for adapter in loaded.values():
        item = adapter.cast(0, "http://localhost:8200")
        assert isinstance(item, dict)
        assert "id" in item
        assert "groundTruth" in item
