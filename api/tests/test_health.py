from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


def test_live():
    response = client.get("/api/v1/health/live")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_ready():
    response = client.get("/api/v1/health/ready")
    assert response.status_code == 200


def test_unknown_route_uses_error_format():
    response = client.get("/api/v1/nope")
    assert response.status_code == 404
    assert response.json()["error"]["code"] == "RESOURCE_NOT_FOUND"
