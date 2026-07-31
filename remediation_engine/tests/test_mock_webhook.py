import json
import sys
from pathlib import Path

from fastapi.testclient import TestClient


ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(ROOT))

from remediation_engine import mock_webhook


client = TestClient(mock_webhook.app)


def test_mock_slack_webhook_stores_notification(tmp_path, monkeypatch):
    notification_log = tmp_path / "mock_slack_notifications.jsonl"
    monkeypatch.setattr(mock_webhook, "NOTIFICATION_LOG", notification_log)

    payload = {
        "text": "Incident INC-1 ouvert",
        "incident_id": "INC-1",
        "machine_id": "unit_42",
    }

    response = client.post("/webhook/slack", json=payload)
    assert response.status_code == 200
    assert response.json()["status"] == "received"

    stored = json.loads(notification_log.read_text().splitlines()[0])
    assert stored["payload"] == payload

    list_response = client.get("/notifications")
    assert list_response.status_code == 200
    assert list_response.json()["notifications"][0]["payload"] == payload
