"""Tests for GET /api/datasets/<name>/images/<filename>."""


def test_serve_existing_image(client):
    resp = client.get("/api/datasets/gqa/images/1000.jpg")
    assert resp.status_code == 200
    assert "image" in resp.content_type


def test_nonexistent_image_returns_404(client):
    resp = client.get("/api/datasets/gqa/images/does_not_exist.jpg")
    assert resp.status_code == 404


def test_no_local_images_returns_404(client):
    """VG adapter has has_local_images=False, so image requests should 404."""
    resp = client.get("/api/datasets/vg/images/anything.jpg")
    assert resp.status_code == 404


def test_nonexistent_dataset_images_returns_404(client):
    resp = client.get("/api/datasets/fake/images/1.jpg")
    assert resp.status_code == 404


def test_path_traversal_blocked(client):
    resp = client.get("/api/datasets/gqa/images/../../etc/passwd")
    assert resp.status_code in (403, 404)


def test_image_has_cache_header(client):
    resp = client.get("/api/datasets/gqa/images/1000.jpg")
    assert "max-age" in resp.headers.get("Cache-Control", "")
