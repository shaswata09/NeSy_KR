"""Tests for GET /api/datasets/<name>?offset=&limit=."""


def test_default_pagination(client):
    resp = client.get("/api/datasets/vg")
    assert resp.status_code == 200
    data = resp.get_json()
    assert data["total"] == 5
    assert data["offset"] == 0
    assert data["limit"] == 50
    assert len(data["items"]) == 5  # fewer than limit


def test_custom_offset_and_limit(client):
    resp = client.get("/api/datasets/vg?offset=1&limit=2")
    data = resp.get_json()
    assert data["offset"] == 1
    assert data["limit"] == 2
    assert len(data["items"]) == 2
    assert data["items"][0]["id"] == "vg_1"
    assert data["items"][1]["id"] == "vg_2"


def test_offset_beyond_total(client):
    resp = client.get("/api/datasets/vg?offset=100")
    data = resp.get_json()
    assert len(data["items"]) == 0
    assert data["offset"] == 5  # clamped to total


def test_limit_capped_at_max(client):
    resp = client.get("/api/datasets/vg?limit=9999")
    data = resp.get_json()
    assert data["limit"] <= 200  # MAX_LIMIT


def test_negative_offset_becomes_zero(client):
    resp = client.get("/api/datasets/vg?offset=-5")
    data = resp.get_json()
    assert data["offset"] == 0


def test_unknown_dataset_returns_404(client):
    resp = client.get("/api/datasets/nonexistent")
    assert resp.status_code == 404


def test_item_has_required_schema(client):
    resp = client.get("/api/datasets/gqa?limit=1")
    data = resp.get_json()
    item = data["items"][0]
    assert "id" in item
    assert "name" in item
    assert "imageUrl" in item
    assert "width" in item
    assert "height" in item
    assert "metadata" in item
    assert "groundTruth" in item
    ground = item["groundTruth"]
    assert "nodes" in ground
    assert "links" in ground
    assert "attributes" in ground
    assert "qas" in ground


def test_gqa_image_url_contains_server_base(client):
    resp = client.get("/api/datasets/gqa?limit=1")
    data = resp.get_json()
    url = data["items"][0]["imageUrl"]
    assert "/api/datasets/gqa/images/" in url
    assert url.startswith("http")
