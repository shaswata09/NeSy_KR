"""Tests for GET /api/datasets."""


def test_datasets_returns_200(client):
    resp = client.get("/api/datasets")
    assert resp.status_code == 200


def test_datasets_returns_list(client):
    data = client.get("/api/datasets").get_json()
    assert isinstance(data, list)
    assert len(data) == 2


def test_datasets_entry_has_required_fields(client):
    data = client.get("/api/datasets").get_json()
    required_keys = {"name", "displayName", "total", "splits", "hasLocalImages"}
    for entry in data:
        assert required_keys.issubset(entry.keys())


def test_datasets_vg_metadata(client):
    data = client.get("/api/datasets").get_json()
    vg = next(d for d in data if d["name"] == "vg")
    assert vg["displayName"] == "Visual Genome"
    assert vg["total"] == 5
    assert vg["splits"] == ["train"]
    assert vg["hasLocalImages"] is False


def test_datasets_gqa_metadata(client):
    data = client.get("/api/datasets").get_json()
    gqa = next(d for d in data if d["name"] == "gqa")
    assert gqa["displayName"] == "GQA"
    assert gqa["total"] == 3
    assert gqa["splits"] == ["train", "val"]
    assert gqa["hasLocalImages"] is True
