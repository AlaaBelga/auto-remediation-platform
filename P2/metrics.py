from threading import Lock
from typing import Dict
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from threading import Thread


_LOCK = Lock()
_ACTION_SAMPLE_LIMIT = 20
_ACTION_SAMPLES: list[dict[str, str]] = []

_METRICS: Dict[str, Dict[str, float | str]] = {
    "p2_events_received_total": {
        "help": "Total number of P1 to P2 events received.",
        "type": "counter",
        "value": 0.0,
    },
    "p2_events_rejected_total": {
        "help": "Total number of P1 to P2 events rejected by schema validation.",
        "type": "counter",
        "value": 0.0,
    },
    "p2_self_healing_triggered_total": {
        "help": "Total number of self-healing playbooks triggered.",
        "type": "counter",
        "value": 0.0,
    },
    "p2_no_action_total": {
        "help": "Total number of valid events that did not trigger self-healing.",
        "type": "counter",
        "value": 0.0,
    },
    "p2_actuator_commands_total": {
        "help": "Total number of simulated actuator commands sent.",
        "type": "counter",
        "value": 0.0,
    },
    "p2_incidents_opened_total": {
        "help": "Total number of simulated incidents opened.",
        "type": "counter",
        "value": 0.0,
    },
    "p2_tickets_created_total": {
        "help": "Total number of mock tickets created in SQLite.",
        "type": "counter",
        "value": 0.0,
    },
    "p2_webhook_notifications_total": {
        "help": "Total number of webhook notifications sent.",
        "type": "counter",
        "value": 0.0,
    },
    "p2_webhook_notification_errors_total": {
        "help": "Total number of webhook notification errors.",
        "type": "counter",
        "value": 0.0,
    },
    "p2_remediation_success_total": {
        "help": "Total number of self-healing remediations completed successfully.",
        "type": "counter",
        "value": 0.0,
    },
    "p2_remediation_failed_total": {
        "help": "Total number of self-healing remediations that failed.",
        "type": "counter",
        "value": 0.0,
    },
    "p2_incidents_resolved_total": {
        "help": "Total number of simulated incidents resolved after remediation.",
        "type": "counter",
        "value": 0.0,
    },
    "p2_active_incidents": {
        "help": "Current number of simulated incidents still active.",
        "type": "gauge",
        "value": 0.0,
    },
    "p2_remediation_duration_seconds": {
        "help": "Latest simulated remediation duration in seconds.",
        "type": "gauge",
        "value": 0.0,
    },
    "p2_latest_risk_score": {
        "help": "Latest risk score observed by P2.",
        "type": "gauge",
        "value": 0.0,
    },
    "p2_latest_risk_after": {
        "help": "Latest risk score after a successful P2 remediation.",
        "type": "gauge",
        "value": 0.0,
    },
    "p2_machine_health_status": {
        "help": "Latest simulated machine health status after P2 processing: 0 healthy, 1 warning, 2 critical.",
        "type": "gauge",
        "value": 0.0,
    },
}


def _escape_label(value: object) -> str:
    return str(value).replace("\\", "\\\\").replace("\n", "\\n").replace('"', '\\"')


def inc_metric(name: str, amount: float = 1.0) -> None:
    with _LOCK:
        _METRICS[name]["value"] = float(_METRICS[name]["value"]) + amount


def set_metric(name: str, value: float) -> None:
    with _LOCK:
        _METRICS[name]["value"] = float(value)


def record_remediation_action(record: dict[str, object]) -> None:
    labels = {
        "time": record.get("time", ""),
        "machine_id": record.get("machine_id", ""),
        "risk_before": record.get("risk_before", ""),
        "action": record.get("action", ""),
        "result": record.get("result", ""),
        "risk_after": record.get("risk_after", ""),
        "incident_status": record.get("incident_status", ""),
        "incident_id": record.get("incident_id", ""),
    }
    with _LOCK:
        _ACTION_SAMPLES.insert(0, {key: str(value) for key, value in labels.items()})
        del _ACTION_SAMPLES[_ACTION_SAMPLE_LIMIT:]


def render_prometheus_metrics() -> str:
    lines = []
    with _LOCK:
        for name, meta in _METRICS.items():
            lines.append(f"# HELP {name} {meta['help']}")
            lines.append(f"# TYPE {name} {meta['type']}")
            lines.append(f"{name} {float(meta['value'])}")
        lines.append("# HELP p2_remediation_action_info Latest P2 remediation actions as info-style labeled samples.")
        lines.append("# TYPE p2_remediation_action_info gauge")
        for sample in _ACTION_SAMPLES:
            labels = ",".join(
                f'{key}="{_escape_label(value)}"' for key, value in sample.items()
            )
            lines.append(f"p2_remediation_action_info{{{labels}}} 1")
    return "\n".join(lines) + "\n"


class _MetricsHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        if self.path == "/health":
            body = b'{"status":"ok"}'
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
        elif self.path == "/metrics":
            body = render_prometheus_metrics().encode("utf-8")
            self.send_response(200)
            self.send_header(
                "Content-Type",
                "text/plain; version=0.0.4; charset=utf-8",
            )
        else:
            body = b"not found"
            self.send_response(404)
            self.send_header("Content-Type", "text/plain")

        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def log_message(self, format, *args):
        return


def start_metrics_http_server(port: int = 8002):
    server = ThreadingHTTPServer(("0.0.0.0", port), _MetricsHandler)
    thread = Thread(target=server.serve_forever, daemon=True)
    thread.start()
    return server
