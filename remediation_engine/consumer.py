#!/usr/bin/env python3
"""Minimal P1 -> P2 event consumer and validator.

Usage: python3 consumer.py path/to/event.json

The script validates required fields and basic types/ranges according to the v1 schema,
logs the event, and simulates triggering a playbook when `decision == 'trigger_self_healing'`.
"""
import json
import os
import sys
import re
import tempfile
import time
from datetime import datetime, timezone
from pathlib import Path
from urllib.error import URLError
from urllib.request import Request, urlopen
from uuid import uuid4

from .validator import quick_validate
from .metrics import inc_metric, record_remediation_action, set_metric
from .ticket_db import create_ticket_from_incident, update_ticket_from_incident

BASE = Path(__file__).resolve().parent
DATA_DIR = Path(
    os.getenv(
        "P2_DATA_DIR",
        Path(tempfile.gettempdir()) / "self-healing-p2",
    )
)
DATA_DIR.mkdir(parents=True, exist_ok=True)

LOG_FILE = DATA_DIR / "consumer.log"
ACTION_LOG = DATA_DIR / "playbook_actions.log"
ACTUATOR_LOG = DATA_DIR / "actuator_commands.log"
INCIDENT_LOG = DATA_DIR / "incidents.jsonl"

EVENT_ID_RE = re.compile(r"^evt-[0-9]{8}-[0-9A-Za-z-]+$")
SCHEMA_VERSION_RE = re.compile(r"^[0-9]+\.[0-9]+$")

ALLOWED_DECISIONS = {"observe", "escalate", "trigger_self_healing", "require_human_review"}
ALLOWED_EVENT_TYPE = "machine_risk_assessed"
ALLOWED_SOURCE = "pilier_1"

ALLOWED_PROPERTIES = {
    "event_id",
    "event_type",
    "timestamp",
    "source",
    "correlation_id",
    "machine_id",
    "prediction",
    "status",
    "risk_score",
    "threshold",
    "decision",
    "model_version",
    "api_latency_ms",
    "confidence",
    "severity",
    "recommended_action",
    "estimated_time_to_failure_hours",
    "anomaly_detected",
    "anomaly_score",
    "top_contributing_sensors",
    "service_health_ok",
    "reason",
    "schema_version",
}


def now_utc():
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def log(msg: str):
    ts = now_utc()
    with open(LOG_FILE, "a") as f:
        f.write(f"{ts} {msg}\n")


def log_action(msg: str):
    ts = now_utc()
    with open(ACTION_LOG, "a") as f:
        f.write(f"{ts} {msg}\n")


def append_json_line(path: Path, payload: dict):
    with open(path, "a") as f:
        f.write(json.dumps(payload, ensure_ascii=False) + "\n")


def webhook_url():
    return os.getenv("P2_WEBHOOK_URL") or os.getenv("SLACK_WEBHOOK_URL")


def build_webhook_payload(ev: dict, incident: dict):
    return {
        "text": (
            f"Incident {incident['incident_id']} {incident.get('status')} pour "
            f"{incident.get('machine_id')} - risque {incident.get('risk_score')} -> {incident.get('risk_after')}"
        ),
        "event_id": incident.get("event_id"),
        "correlation_id": incident.get("correlation_id"),
        "machine_id": incident.get("machine_id"),
        "severity": incident.get("severity"),
        "status": incident.get("status"),
        "risk_score": incident.get("risk_score"),
        "risk_after": incident.get("risk_after"),
        "recommended_action": incident.get("recommended_action"),
        "playbook_result": incident.get("playbook_result"),
        "remediation_duration_seconds": incident.get("remediation_duration_seconds"),
        "source_decision": ev.get("decision"),
        "created_at": incident.get("created_at"),
        "resolved_at": incident.get("resolved_at"),
    }


def send_webhook_notification(ev: dict, incident: dict):
    from .notifications import NotificationManager

    manager = NotificationManager()
    return manager.send_notification(ev, incident)


def validate_event(ev: dict):
    # Required fields
    required = [
        "event_id",
        "event_type",
        "timestamp",
        "source",
        "correlation_id",
        "machine_id",
        "prediction",
        "risk_score",
        "decision",
        "schema_version",
    ]
    for r in required:
        if r not in ev:
            return False, f"missing required field: {r}"

    # No additional properties
    for k in ev.keys():
        if k not in ALLOWED_PROPERTIES:
            return False, f"unexpected property: {k}"

    # event_id pattern
    if not isinstance(ev["event_id"], str) or not EVENT_ID_RE.match(ev["event_id"]):
        return False, "invalid event_id format"

    # event_type
    if ev.get("event_type") != ALLOWED_EVENT_TYPE:
        return False, f"invalid event_type: {ev.get('event_type')!r}"

    # source
    if ev.get("source") != ALLOWED_SOURCE:
        return False, f"invalid source: {ev.get('source')!r}"

    # timestamp
    try:
        # Accept ISO8601-like strings
        datetime.fromisoformat(ev["timestamp"].replace("Z", "+00:00"))
    except Exception:
        return False, "invalid timestamp format"

    # prediction
    if not (isinstance(ev["prediction"], int) and ev["prediction"] in (0, 1)):
        return False, "prediction must be integer 0 or 1"

    # risk_score
    try:
        rs = float(ev["risk_score"])
    except Exception:
        return False, "risk_score must be a number"
    if not (0.0 <= rs <= 1.0):
        return False, "risk_score must be between 0 and 1"

    # decision
    if ev["decision"] not in ALLOWED_DECISIONS:
        return False, f"invalid decision: {ev['decision']!r}"

    # schema_version
    if not isinstance(ev["schema_version"], str) or not SCHEMA_VERSION_RE.match(ev["schema_version"]):
        return False, "invalid schema_version"

    return True, "ok"


ACTION_COMMANDS = {
    "restart_service": "RESTART_CONTROLLER_SERVICE",
    "reduce_load": "REDUCE_LOAD_TO_60_PERCENT",
    "recalibrate_sensor": "RECALIBRATE_ABNORMAL_SENSOR",
    "schedule_maintenance": "SCHEDULE_URGENT_MAINTENANCE",
}


def unique_actions(actions: list[str]) -> list[str]:
    result = []
    for action in actions:
        if action not in result:
            result.append(action)
    return result


def select_remediation_actions(ev: dict) -> list[str]:
    risk_score = float(ev.get("risk_score") or 0.0)
    estimated_hours = ev.get("estimated_time_to_failure_hours")
    anomaly_detected = bool(ev.get("anomaly_detected", False))
    sensors = set(ev.get("top_contributing_sensors") or [])
    service_health_ok = bool(ev.get("service_health_ok", True))
    recommended_action = ev.get("recommended_action")

    actions = []
    if risk_score >= 0.90:
        actions.append("reduce_load")

    if isinstance(estimated_hours, (int, float)) and estimated_hours < 10:
        actions.append("schedule_maintenance")

    if anomaly_detected or {"sensor_11", "sensor_4"} & sensors:
        actions.append("recalibrate_sensor")

    if not service_health_ok or recommended_action == "restart_service":
        actions.append("restart_service")

    if recommended_action in ACTION_COMMANDS:
        actions.append(str(recommended_action))

    return unique_actions(actions or ["restart_service"])


def risk_after_actions(risk_before: float, actions: list[str]) -> float:
    risk_after = risk_before
    if "reduce_load" in actions:
        risk_after = min(risk_after, 0.40)
    if "recalibrate_sensor" in actions:
        risk_after = min(risk_after, 0.35)
    if "schedule_maintenance" in actions:
        risk_after = min(risk_after, 0.30)
    if "restart_service" in actions:
        risk_after = min(risk_after, 0.21)
    if len(actions) >= 3:
        risk_after = min(risk_after, 0.08)
    return round(max(risk_after, 0.0), 3)


def simulate_actuator_command(ev: dict, action: str):
    command = {
        "command_id": f"cmd-{uuid4().hex[:12]}",
        "event_id": ev.get("event_id"),
        "correlation_id": ev.get("correlation_id"),
        "machine_id": ev.get("machine_id"),
        "action": action,
        "command": ACTION_COMMANDS[action],
        "status": "sent",
        "timestamp": now_utc(),
    }
    append_json_line(ACTUATOR_LOG, command)
    inc_metric("p2_actuator_commands_total")
    log_action(
        f"actuator_command command_id={command['command_id']} machine={command['machine_id']} command={command['command']} status={command['status']}"
    )
    return command


def create_incident(ev: dict, playbook_result: str, actuator_commands: list[dict], actions: list[str]):
    action_summary = " + ".join(actions)
    incident = {
        "incident_id": f"INC-{datetime.now(timezone.utc).strftime('%Y%m%d')}-{uuid4().hex[:8].upper()}",
        "event_id": ev.get("event_id"),
        "correlation_id": ev.get("correlation_id"),
        "machine_id": ev.get("machine_id"),
        "severity": ev.get("severity") or "high",
        "status": "opened",
        "risk_score": ev.get("risk_score"),
        "recommended_action": action_summary,
        "remediation_actions": actions,
        "playbook_result": playbook_result,
        "actuator_command_id": actuator_commands[0].get("command_id") if actuator_commands else None,
        "actuator_command_ids": [command.get("command_id") for command in actuator_commands],
        "created_at": now_utc(),
    }
    ticket = create_ticket_from_incident(incident)
    incident["ticket_id"] = ticket["ticket_id"]
    append_json_line(INCIDENT_LOG, incident)
    inc_metric("p2_incidents_opened_total")
    inc_metric("p2_active_incidents")
    inc_metric("p2_tickets_created_total")
    log_action(
        f"incident_created incident_id={incident['incident_id']} ticket_id={incident['ticket_id']} machine={incident['machine_id']} severity={incident['severity']} status={incident['status']}"
    )
    return incident


def resolve_incident(ev: dict, incident: dict, started_at: float, actions: list[str]):
    duration_seconds = round(time.perf_counter() - started_at, 3)
    risk_before = float(ev.get("risk_score") or 0.0)
    risk_after = risk_after_actions(risk_before, actions)
    action_summary = " + ".join(actions)

    incident.update(
        {
            "status": "resolved",
            "risk_before": risk_before,
            "risk_after": risk_after,
            "machine_state_before": "CRITICAL",
            "machine_state_after": "HEALTHY" if risk_after < 0.7 else "WARNING",
            "resolved_at": now_utc(),
            "remediation_duration_seconds": duration_seconds,
        }
    )
    update_ticket_from_incident(incident)
    append_json_line(INCIDENT_LOG, incident)
    inc_metric("p2_incidents_resolved_total")
    inc_metric("p2_active_incidents", -1)
    set_metric("p2_latest_risk_after", risk_after)
    set_metric("p2_latest_risk_score", risk_after)
    set_metric("p2_machine_health_status", 0.0 if risk_after < 0.7 else 1.0)
    set_metric("p2_remediation_duration_seconds", duration_seconds)
    record_remediation_action(
        {
            "time": incident["resolved_at"],
            "machine_id": incident.get("machine_id"),
            "risk_before": risk_before,
            "action": action_summary,
            "result": incident.get("playbook_result"),
            "risk_after": risk_after,
            "incident_status": incident.get("status"),
            "incident_id": incident.get("incident_id"),
        }
    )
    log_action(
        f"incident_resolved incident_id={incident['incident_id']} ticket_id={incident['ticket_id']} machine={incident['machine_id']} action={action_summary} risk_before={risk_before} risk_after={risk_after} duration_seconds={duration_seconds}"
    )
    return incident


def simulate_playbook(ev: dict):
    started_at = time.perf_counter()
    actions = select_remediation_actions(ev)
    action_summary = " + ".join(actions)
    # Simple simulation: mark success if api_latency_ms is not extremely high
    latency = ev.get("api_latency_ms")
    if isinstance(latency, int) and latency > 5000:
        result = "failed_due_to_high_latency"
    else:
        result = "success"
    log_action(f"playbook: {action_summary} machine={ev.get('machine_id')} decision={ev.get('decision')} result={result}")

    actuator_commands = [simulate_actuator_command(ev, action) for action in actions]
    incident = create_incident(ev, result, actuator_commands, actions)
    if result == "success":
        inc_metric("p2_remediation_success_total")
        incident = resolve_incident(ev, incident, started_at, actions)
    else:
        inc_metric("p2_remediation_failed_total")
        set_metric("p2_machine_health_status", 2.0)
        set_metric("p2_remediation_duration_seconds", round(time.perf_counter() - started_at, 3))
    notification = send_webhook_notification(ev, incident)

    return {
        "playbook": "critical_machine_risk",
        "actions": actions,
        "result": result,
        "machine_id": ev.get("machine_id"),
        "actuator": actuator_commands[0] if actuator_commands else None,
        "actuators": actuator_commands,
        "incident": incident,
        "notification": notification,
    }


def main():
    if len(sys.argv) < 2:
        print("Usage: python3 consumer.py path/to/event.json")
        sys.exit(2)

    p = Path(sys.argv[1])
    if not p.exists():
        print(f"File not found: {p}")
        sys.exit(2)

    ev = json.loads(p.read_text())
    valid, reason = quick_validate(ev)
    if not valid:
        msg = f"validation_error event_id={ev.get('event_id', 'NA')} reason={reason}"
        print(msg)
        log(msg)
        sys.exit(1)

    msg = f"validated event_id={ev['event_id']} machine={ev['machine_id']} decision={ev['decision']} risk_score={ev['risk_score']}"
    print(msg)
    log(msg)

    if ev.get("decision") == "trigger_self_healing":
        result = simulate_playbook(ev)
        print(f"playbook result: {result}")
    else:
        print("no playbook triggered")


if __name__ == "__main__":
    main()
