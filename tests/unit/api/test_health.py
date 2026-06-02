from fastapi.testclient import TestClient

from vuls.api.app import create_api_app


def test_health_returns_ok_status() -> None:
    client = TestClient(create_api_app())

    response = client.get("/health")

    assert response.status_code == 200
    assert response.json()["status"] == "ok"
