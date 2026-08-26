import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(ROOT))

from remediation_engine.notifications import NotificationManager


class DummyResponse:
    status = 200

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, tb):
        return False

    def read(self):
        return b"ok"


def test_notification_manager_sends_webhook(monkeypatch):
    sent = {}

    def fake_urlopen(request, timeout=None):
        sent["url"] = request.full_url
        sent["timeout"] = timeout
        sent["method"] = request.get_method()
        sent["body"] = json.loads(request.data.decode("utf-8"))
        return DummyResponse()

    monkeypatch.setenv("P2_WEBHOOK_URL", "https://example.test/webhook")
    monkeypatch.setattr("remediation_engine.notifications.urlopen", fake_urlopen)

    manager = NotificationManager()
    result = manager.send_notification(
        {"event_id": "evt-00000001-test", "decision": "trigger_self_healing"},
        {"incident_id": "INC-20260101-ABCDEF12", "machine_id": "machine-7", "risk_score": 0.95, "risk_after": 0.2},
    )

    assert result["sent"] is True
    assert sent["url"] == "https://example.test/webhook"
    assert sent["method"] == "POST"
    assert sent["body"]["event_id"] == "evt-00000001-test"
    assert sent["body"]["machine_id"] == "machine-7"


def test_notification_manager_uses_channel_interface():
    class RecordingChannel:
        def __init__(self):
            self.payloads = []

        def send(self, payload):
            self.payloads.append(payload)
            return {"sent": True, "channel": "recording"}

    channel = RecordingChannel()
    manager = NotificationManager(channel=channel)

    result = manager.send_notification(
        {"event_id": "evt-00000002-test", "decision": "observe"},
        {"incident_id": "INC-20260101-ABCDEF13", "machine_id": "machine-9", "risk_score": 0.62, "risk_after": 0.55},
    )

    assert result["sent"] is True
    assert result["channel"] == "recording"
    assert channel.payloads[0]["machine_id"] == "machine-9"
