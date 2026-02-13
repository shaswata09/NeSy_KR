"""Tests for GET /api/health."""


def test_health_returns_200(client):
    resp = client.get("/api/health")
    assert resp.status_code == 200


def test_health_has_ok_status(client):
    data = client.get("/api/health").get_json()
    assert data["status"] == "ok"


def test_health_lists_all_datasets(client):
    data = client.get("/api/health").get_json()
    assert "vg" in data["datasets"]
    assert "gqa" in data["datasets"]


def test_health_dataset_has_total(client):
    data = client.get("/api/health").get_json()
    assert data["datasets"]["vg"]["total"] == 5
    assert data["datasets"]["gqa"]["total"] == 3


def test_health_dataset_status_ok(client):
    data = client.get("/api/health").get_json()
    assert data["datasets"]["vg"]["status"] == "ok"
    assert data["datasets"]["gqa"]["status"] == "ok"


def test_health_cors_header(client):
    resp = client.get("/api/health")
    # flask-cors adds Access-Control-Allow-Origin
    assert resp.headers.get("Access-Control-Allow-Origin") is not None
