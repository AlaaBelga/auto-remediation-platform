import json
import os
import sqlite3
import tempfile
from pathlib import Path
from typing import Optional


def data_dir() -> Path:
    path = Path(
        os.getenv(
            "P2_DATA_DIR",
            Path(tempfile.gettempdir()) / "self-healing-p2",
        )
    )
    path.mkdir(parents=True, exist_ok=True)
    return path


def database_path() -> Path:
    return Path(os.getenv("P2_TICKET_DB_PATH", data_dir() / "tickets.db"))


def connect() -> sqlite3.Connection:
    connection = sqlite3.connect(database_path())
    connection.row_factory = sqlite3.Row
    return connection


def init_db() -> None:
    with connect() as connection:
        connection.execute(
            """
            CREATE TABLE IF NOT EXISTS tickets (
                ticket_id TEXT PRIMARY KEY,
                incident_id TEXT NOT NULL UNIQUE,
                event_id TEXT,
                correlation_id TEXT,
                machine_id TEXT,
                severity TEXT,
                status TEXT NOT NULL,
                risk_score REAL,
                recommended_action TEXT,
                playbook_result TEXT,
                actuator_command_id TEXT,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL,
                payload_json TEXT NOT NULL
            )
            """
        )
        connection.execute(
            "CREATE INDEX IF NOT EXISTS idx_tickets_machine_id ON tickets(machine_id)"
        )
        connection.execute(
            "CREATE INDEX IF NOT EXISTS idx_tickets_status ON tickets(status)"
        )


def row_to_ticket(row: sqlite3.Row) -> dict:
    ticket = dict(row)
    ticket["payload"] = json.loads(ticket.pop("payload_json"))
    return ticket


def create_ticket_from_incident(incident: dict) -> dict:
    init_db()
    ticket_id = f"TCK-{incident['incident_id'].removeprefix('INC-')}"
    created_at = incident["created_at"]
    payload_json = json.dumps(incident, ensure_ascii=False)

    with connect() as connection:
        connection.execute(
            """
            INSERT OR REPLACE INTO tickets (
                ticket_id,
                incident_id,
                event_id,
                correlation_id,
                machine_id,
                severity,
                status,
                risk_score,
                recommended_action,
                playbook_result,
                actuator_command_id,
                created_at,
                updated_at,
                payload_json
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                ticket_id,
                incident["incident_id"],
                incident.get("event_id"),
                incident.get("correlation_id"),
                incident.get("machine_id"),
                incident.get("severity"),
                "opened",
                float(incident.get("risk_score") or 0.0),
                incident.get("recommended_action"),
                incident.get("playbook_result"),
                incident.get("actuator_command_id"),
                created_at,
                created_at,
                payload_json,
            ),
        )

    return get_ticket(ticket_id)


def update_ticket_from_incident(incident: dict) -> dict:
    init_db()
    ticket_id = incident.get("ticket_id") or f"TCK-{incident['incident_id'].removeprefix('INC-')}"
    updated_at = incident.get("resolved_at") or incident.get("updated_at") or incident["created_at"]
    payload_json = json.dumps(incident, ensure_ascii=False)

    with connect() as connection:
        connection.execute(
            """
            UPDATE tickets
            SET status = ?,
                risk_score = ?,
                playbook_result = ?,
                updated_at = ?,
                payload_json = ?
            WHERE ticket_id = ?
            """,
            (
                incident.get("status", "opened"),
                float(incident.get("risk_after", incident.get("risk_score")) or 0.0),
                incident.get("playbook_result"),
                updated_at,
                payload_json,
                ticket_id,
            ),
        )

    return get_ticket(ticket_id)


def list_tickets(limit: int = 50, status: Optional[str] = None) -> list[dict]:
    init_db()
    limit = max(1, min(int(limit), 200))

    with connect() as connection:
        if status:
            rows = connection.execute(
                """
                SELECT * FROM tickets
                WHERE status = ?
                ORDER BY created_at DESC
                LIMIT ?
                """,
                (status, limit),
            ).fetchall()
        else:
            rows = connection.execute(
                """
                SELECT * FROM tickets
                ORDER BY created_at DESC
                LIMIT ?
                """,
                (limit,),
            ).fetchall()
    return [row_to_ticket(row) for row in rows]


def get_ticket(ticket_id: str) -> dict | None:
    init_db()
    with connect() as connection:
        row = connection.execute(
            "SELECT * FROM tickets WHERE ticket_id = ?",
            (ticket_id,),
        ).fetchone()
    return row_to_ticket(row) if row else None
