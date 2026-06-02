from fastapi.testclient import TestClient

from vuls.api.app import create_api_app


def test_telegram_webhook_rejects_invalid_secret() -> None:
    client = TestClient(create_api_app(telegram_webhook_secret="expected-secret"))

    response = client.post("/webhooks/telegram/wrong-secret", json={"update_id": 1})

    assert response.status_code == 403
    assert response.json() == {
        "error": {
            "code": "invalid_webhook_secret",
            "message": "Invalid Telegram webhook secret",
        }
    }
