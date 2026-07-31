import json
import os
import tempfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict

from fastapi import FastAPI


DATA_DIR = Path(
    os.getenv(
        "P2_DATA_DIR",
        Path(tempfile.gettempdir()) / "self-healing-p2",
    )
)
DATA_DIR.mkdir(parents=True, exist_ok=True)

NOTIFICATION_LOG = DATA_DIR / "mock_slack_notifications.jsonl"

app = FastAPI(title="Mock Slack Webhook")


def now_utc():
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def append_notification(payload: dict):
    record = {
        "received_at": now_utc(),
        "payload": payload,
    }
    with open(NOTIFICATION_LOG, "a") as handle:
        handle.write(json.dumps(record, ensure_ascii=False) + "\n")
    return record


@app.get("/health")
def health():
    return {"status": "ok"}


@app.post("/webhook/slack")
def receive_slack_webhook(payload: Dict[str, Any]):
    record = append_notification(payload)
    return {
        "status": "received",
        "stored_in": str(NOTIFICATION_LOG),
        "received_at": record["received_at"],
    }


@app.get("/notifications")
def list_notifications(limit: int = 20):
    if not NOTIFICATION_LOG.exists():
        return {"notifications": []}

    lines = NOTIFICATION_LOG.read_text().splitlines()
    records = [json.loads(line) for line in lines[-limit:]]
    return {"notifications": records}
