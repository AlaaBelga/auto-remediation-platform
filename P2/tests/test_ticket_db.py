import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(ROOT))

from P2.ticket_db import create_ticket_from_incident, get_ticket, list_tickets, update_ticket_from_incident


def test_create_and_read_ticket_from_sqlite(tmp_path, monkeypatch):
    monkeypatch.setenv("P2_TICKET_DB_PATH", str(tmp_path / "tickets.db"))
    incident = {
        "incident_id": "INC-20260607-ABC12345",
        "event_id": "evt-20260607-test",
        "correlation_id": "corr-test",
        "machine_id": "unit_42",
        "severity": "high",
        "status": "opened",
        "risk_score": 0.93,
        "recommended_action": "restart_service",
        "playbook_result": "success",
        "actuator_command_id": "cmd-test",
        "created_at": "2026-06-07T10:00:00Z",
    }

    ticket = create_ticket_from_incident(incident)

    assert ticket["ticket_id"] == "TCK-20260607-ABC12345"
    assert ticket["incident_id"] == incident["incident_id"]
    assert ticket["machine_id"] == "unit_42"
    assert ticket["status"] == "opened"
    assert ticket["payload"]["recommended_action"] == "restart_service"

    assert get_ticket(ticket["ticket_id"])["incident_id"] == incident["incident_id"]
    assert list_tickets()[0]["ticket_id"] == ticket["ticket_id"]

    incident.update(
        {
            "ticket_id": ticket["ticket_id"],
            "status": "resolved",
            "risk_after": 0.21,
            "resolved_at": "2026-06-07T10:01:00Z",
        }
    )
    updated_ticket = update_ticket_from_incident(incident)

    assert updated_ticket["status"] == "resolved"
    assert updated_ticket["risk_score"] == 0.21
    assert updated_ticket["payload"]["status"] == "resolved"
