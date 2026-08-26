import json
import os
from abc import ABC, abstractmethod
from urllib.error import URLError
from urllib.request import Request, urlopen

from .metrics import inc_metric


class NotificationChannel(ABC):
    """Contract for any transport that can send an incident payload."""

    @abstractmethod
    def send(self, payload: dict):
        """Send a notification payload and return a result dictionary."""


class WebhookNotificationChannel(NotificationChannel):
    """Default channel that posts incident data to a configured webhook."""

    def __init__(self, webhook_url: str | None = None, timeout_seconds: float | None = None):
        self.webhook_url = webhook_url or os.getenv("P2_WEBHOOK_URL") or os.getenv("SLACK_WEBHOOK_URL")
        self.timeout_seconds = timeout_seconds
        if self.timeout_seconds is None:
            try:
                self.timeout_seconds = float(os.getenv("P2_WEBHOOK_TIMEOUT_SECONDS", "3"))
            except ValueError:
                self.timeout_seconds = 3.0

    def send(self, payload: dict):
        from .consumer import log_action

        url = self.webhook_url
        if not url:
            return {"sent": False, "reason": "webhook_disabled"}

        body = json.dumps(payload).encode("utf-8")
        request = Request(
            url,
            data=body,
            headers={"Content-Type": "application/json"},
            method="POST",
        )

        try:
            with urlopen(request, timeout=self.timeout_seconds) as response:
                response_body = response.read().decode("utf-8", errors="replace")
            inc_metric("p2_webhook_notifications_total")
            log_action(
                f"webhook_notification_sent incident_id={payload.get('event_id')} url={url} status={response.status}"
            )
            return {
                "sent": True,
                "status_code": response.status,
                "response": response_body,
            }
        except (OSError, URLError) as exc:
            inc_metric("p2_webhook_notification_errors_total")
            log_action(
                f"webhook_notification_error incident_id={payload.get('event_id')} url={url} error={exc}"
            )
            return {
                "sent": False,
                "reason": "webhook_error",
                "error": str(exc),
            }


class NotificationManager:
    """Centralizes outgoing incident notifications for the self-healing pipeline."""

    def __init__(self, channel: NotificationChannel | None = None, webhook_url: str | None = None, timeout_seconds: float | None = None):
        self.channel = channel or WebhookNotificationChannel(webhook_url=webhook_url, timeout_seconds=timeout_seconds)

    def build_payload(self, ev: dict, incident: dict):
        return {
            "text": (
                f"Incident {incident['incident_id']} {incident.get('status')} pour "
                f"{incident.get('machine_id')} - risque {incident.get('risk_score')} -> {incident.get('risk_after')}"
            ),
            "event_id": incident.get("event_id") or ev.get("event_id"),
            "correlation_id": incident.get("correlation_id") or ev.get("correlation_id"),
            "machine_id": incident.get("machine_id") or ev.get("machine_id"),
            "severity": incident.get("severity") or ev.get("severity"),
            "status": incident.get("status") or "opened",
            "risk_score": incident.get("risk_score") or ev.get("risk_score"),
            "risk_after": incident.get("risk_after") or ev.get("risk_after"),
            "recommended_action": incident.get("recommended_action") or ev.get("recommended_action"),
            "playbook_result": incident.get("playbook_result") or ev.get("playbook_result"),
            "remediation_duration_seconds": incident.get("remediation_duration_seconds") or ev.get("remediation_duration_seconds"),
            "source_decision": ev.get("decision"),
            "created_at": incident.get("created_at") or ev.get("timestamp"),
            "resolved_at": incident.get("resolved_at"),
        }

    def send_notification(self, ev: dict, incident: dict):
        payload = self.build_payload(ev, incident)
        return self.channel.send(payload)
