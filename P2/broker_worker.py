"""Kafka worker for P1 -> P2 self-healing events.

The worker consumes JSON events from Kafka, validates them using the existing schema,
and simulates remediations while optionally emitting results to an output topic.
"""
import signal
import os
import time
from threading import Event
from typing import Any, Dict, Iterable, Optional

from .consumer import simulate_playbook, log, log_action
from .kafka_integration import load_kafka_config, create_consumer, publish_event
from .metrics import inc_metric, set_metric, start_metrics_http_server
from .validator import quick_validate


def process_event(event: Dict[str, Any]) -> Dict[str, Any]:
    inc_metric("p2_events_received_total")
    try:
        set_metric("p2_latest_risk_score", float(event.get("risk_score", 0.0)))
    except (TypeError, ValueError):
        pass

    valid, reason = quick_validate(event)
    if not valid:
        inc_metric("p2_events_rejected_total")
        result = {
            "status": "rejected",
            "reason": reason,
            "event_id": event.get("event_id"),
            "correlation_id": event.get("correlation_id"),
        }
        log(f"kafka_rejected event_id={event.get('event_id')} reason={reason}")
        return result

    log(
        f"kafka_validated event_id={event.get('event_id')} machine={event.get('machine_id')} decision={event.get('decision')} risk_score={event.get('risk_score')}"
    )

    if event.get("decision") == "trigger_self_healing":
        inc_metric("p2_self_healing_triggered_total")
        outcome = simulate_playbook(event)
        log_action(
            f"kafka_playbook event_id={event.get('event_id')} machine={event.get('machine_id')} result={outcome}"
        )
        payload = {
            "status": "action_triggered",
            "result": outcome,
            "event_id": event.get("event_id"),
            "correlation_id": event.get("correlation_id"),
        }
    else:
        inc_metric("p2_no_action_total")
        payload = {
            "status": "no_action",
            "detail": "decision does not request self-healing",
            "event_id": event.get("event_id"),
            "correlation_id": event.get("correlation_id"),
        }

    config = load_kafka_config()
    if config.enabled:
        publish_event(payload, topic=config.output_topic, key=event.get("correlation_id") or event.get("event_id"))
    return payload


def _drain_messages(messages: Iterable[Any]):
    for message in messages:
        yield message


def run_worker_once():
    consumer = create_consumer()
    for message in consumer:
        return process_event(message.value)
    return {"status": "idle"}


def run_worker_forever(
    stop_event: Optional[Event] = None,
    poll_timeout_ms: int = 1000,
    max_messages: Optional[int] = None,
):
    """Continuously poll Kafka and process messages until interrupted.

    This uses KafkaConsumer.poll so the loop can stay alive even when topics are idle,
    and so tests can inject a fake consumer with the same minimal API.
    """
    consumer = create_consumer()
    config = load_kafka_config()
    stop_event = stop_event or Event()

    log(f"kafka_worker_start topic={config.input_topic} bootstrap={config.bootstrap_servers}")

    processed = 0

    try:
        while not stop_event.is_set():
            batches = consumer.poll(timeout_ms=poll_timeout_ms)
            if not batches:
                continue

            for records in batches.values():
                for record in _drain_messages(records):
                    process_event(record.value)
                    processed += 1
                    if max_messages is not None and processed >= max_messages:
                        stop_event.set()
                        break
                if stop_event.is_set():
                    break
    except KeyboardInterrupt:
        log("kafka_worker_interrupt")
    finally:
        try:
            consumer.close()
        except Exception:
            pass
        log("kafka_worker_stop")
    return {"status": "stopped"}


def main():
    metrics_port = int(os.getenv("P2_WORKER_METRICS_PORT", "8002"))
    start_metrics_http_server(metrics_port)
    log(f"kafka_worker_metrics_started port={metrics_port}")
    result = run_worker_forever()
    print(result)


if __name__ == "__main__":
    main()
