import json
import sys
from pathlib import Path
from fastapi.testclient import TestClient

# Ensure repo root is on sys.path for imports
ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(ROOT))

from remediation_engine.api import app
from remediation_engine import kafka_integration


BASE = Path(__file__).resolve().parent.parent


def load(name: str):
    return json.loads((BASE / "examples" / name).read_text())


client = TestClient(app)


def test_post_valid_triggers_action():
    ev = load("event_valid.json")
    resp = client.post("/events", json=ev)
    assert resp.status_code == 200
    j = resp.json()
    assert j["status"] == "action_triggered"
    assert "result" in j
    assert j["result"]["actuator"]["status"] == "sent"
    assert j["result"]["actions"] == [
        "reduce_load",
        "schedule_maintenance",
        "recalibrate_sensor",
        "restart_service",
    ]
    assert j["result"]["incident"]["status"] == "resolved"
    assert j["result"]["incident"]["risk_after"] < j["result"]["incident"]["risk_before"]


def test_post_invalid_rejected():
    ev = load("event_invalid.json")
    resp = client.post("/events", json=ev)
    assert resp.status_code == 400
    j = resp.json()
    assert "validation_error" in j["detail"]


def test_events_requires_api_key_when_configured(monkeypatch):
    monkeypatch.setenv("P2_API_KEY", "secret-test-key")
    ev = load("event_valid.json")

    missing_key_response = client.post("/events", json=ev)
    assert missing_key_response.status_code == 401

    valid_key_response = client.post(
        "/events",
        json=ev,
        headers={"X-API-Key": "secret-test-key"},
    )
    assert valid_key_response.status_code == 200


def test_ui_route_renders_dashboard():
    resp = client.get("/ui")
    assert resp.status_code == 200
    assert "text/html" in resp.headers.get("content-type", "")
    assert "Console P2 d'auto-remediation" in resp.text


def test_metrics_route_exposes_prometheus_text():
    resp = client.get("/metrics")
    assert resp.status_code == 200
    assert "text/plain" in resp.headers.get("content-type", "")
    assert "# TYPE p2_events_received_total counter" in resp.text
    assert "p2_self_healing_triggered_total" in resp.text
    assert "p2_actuator_commands_total" in resp.text
    assert "p2_remediation_success_total" in resp.text
    assert "p2_incidents_resolved_total" in resp.text
    assert "p2_active_incidents" in resp.text
    assert "p2_remediation_action_info" in resp.text


def test_tickets_route_exposes_mock_ticket_db(tmp_path, monkeypatch):
    monkeypatch.setenv("P2_TICKET_DB_PATH", str(tmp_path / "tickets.db"))
    ev = load("event_valid.json")

    event_response = client.post("/events", json=ev)
    assert event_response.status_code == 200
    ticket_id = event_response.json()["result"]["incident"]["ticket_id"]

    tickets_response = client.get("/tickets")
    assert tickets_response.status_code == 200
    tickets = tickets_response.json()["tickets"]
    assert tickets[0]["ticket_id"] == ticket_id

    ticket_response = client.get(f"/tickets/{ticket_id}")
    assert ticket_response.status_code == 200
    ticket = ticket_response.json()
    assert ticket["ticket_id"] == ticket_id
    assert ticket["event_id"] == ev["event_id"]
    assert ticket["machine_id"] == ev["machine_id"]
    assert ticket["status"] == "resolved"
    assert ticket["payload"]["risk_after"] < ticket["payload"]["risk_before"]


def test_kafka_mode_queues_without_local_action(monkeypatch):
    ev = load("event_valid.json")
    monkeypatch.setattr(
        "remediation_engine.api.load_kafka_config",
        lambda: kafka_integration.KafkaConfig(
            True,
            "localhost:9092",
            "in-topic",
            "out-topic",
            "api-client",
        ),
    )
    monkeypatch.setattr(
        "remediation_engine.api.publish_event",
        lambda *args, **kwargs: {
            "published": True,
            "topic": "in-topic",
            "partition": 0,
            "offset": 1,
        },
    )
    monkeypatch.setattr(
        "remediation_engine.api.simulate_playbook",
        lambda payload: (_ for _ in ()).throw(
            AssertionError("local playbook must not run in Kafka mode")
        ),
    )

    response = client.post("/events", json=ev)
    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "queued"
    assert body["kafka"]["published"] is True
