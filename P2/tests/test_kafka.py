import json
import sys
from pathlib import Path
from threading import Event

ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(ROOT))

from P2 import kafka_integration
from P2.broker_worker import process_event


BASE = Path(__file__).resolve().parent.parent


def load(name: str):
    return json.loads((BASE / "examples" / name).read_text())


def test_process_event_triggers_action(monkeypatch):
    ev = load("event_valid.json")

    monkeypatch.setattr("P2.broker_worker.load_kafka_config", lambda: kafka_integration.KafkaConfig(True, "localhost:9092", "in-topic", "out-topic", "client-1"))
    monkeypatch.setattr("P2.broker_worker.publish_event", lambda *args, **kwargs: {"published": True})

    result = process_event(ev)
    assert result["status"] == "action_triggered"
    assert result["result"]["result"] == "success"
    assert result["result"]["actions"] == [
        "reduce_load",
        "schedule_maintenance",
        "recalibrate_sensor",
        "restart_service",
    ]
    assert result["result"]["actuator"]["command"] == "REDUCE_LOAD_TO_60_PERCENT"
    assert result["result"]["incident"]["status"] == "resolved"
    assert result["result"]["incident"]["machine_state_after"] == "HEALTHY"


def test_process_event_sends_webhook_notification(monkeypatch):
    ev = load("event_valid.json")
    calls = []

    monkeypatch.setattr("P2.broker_worker.load_kafka_config", lambda: kafka_integration.KafkaConfig(False, "localhost:9092", "in-topic", "out-topic", "client-1"))
    monkeypatch.setattr(
        "P2.consumer.send_webhook_notification",
        lambda event, incident: calls.append((event, incident)) or {"sent": True},
    )

    result = process_event(ev)

    assert result["status"] == "action_triggered"
    assert result["result"]["notification"] == {"sent": True}
    assert len(calls) == 1
    assert calls[0][1]["status"] == "resolved"


def test_process_event_rejects_invalid_payload():
    ev = load("event_invalid.json")
    result = process_event(ev)
    assert result["status"] == "rejected"
    assert "reason" in result


def test_publish_event_returns_disabled_when_kafka_off(monkeypatch):
    ev = load("event_valid.json")
    monkeypatch.setattr("P2.kafka_integration.load_kafka_config", lambda: kafka_integration.KafkaConfig(False, "localhost:9092", "in-topic", "out-topic", "client-1"))
    result = kafka_integration.publish_event(ev)
    assert result == {"published": False, "reason": "kafka_disabled"}


def test_run_worker_forever_processes_one_batch_and_stops(monkeypatch):
    ev = load("event_valid.json")
    fake_message = type("FakeMessage", (), {"value": ev})()

    class FakeConsumer:
        def __init__(self):
            self.closed = False
            self.calls = 0

        def poll(self, timeout_ms=1000):
            self.calls += 1
            if self.calls == 1:
                return {0: [fake_message]}
            return {}

        def close(self):
            self.closed = True

    fake_consumer = FakeConsumer()

    monkeypatch.setattr("P2.broker_worker.create_consumer", lambda: fake_consumer)
    monkeypatch.setattr("P2.broker_worker.load_kafka_config", lambda: kafka_integration.KafkaConfig(False, "localhost:9092", "in-topic", "out-topic", "client-1"))
    monkeypatch.setattr("P2.broker_worker.process_event", lambda event: {"status": "action_triggered", "result": "success"})

    stop_event = Event()
    result = __import__("P2.broker_worker", fromlist=["run_worker_forever"]).run_worker_forever(
        stop_event=stop_event,
        poll_timeout_ms=1,
        max_messages=1,
    )
    assert result == {"status": "stopped"}
    assert fake_consumer.closed is True
