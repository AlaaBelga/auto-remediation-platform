import os

from fastapi import Depends, FastAPI, Header, HTTPException
from fastapi.responses import HTMLResponse, PlainTextResponse, RedirectResponse
from typing import Any, Dict
from .validator import quick_validate
from .consumer import simulate_playbook, log
from .ui import render_dashboard_html
from .kafka_integration import load_kafka_config, publish_event
from .metrics import inc_metric, render_prometheus_metrics, set_metric
from .ticket_db import get_ticket, list_tickets

app = FastAPI(title="P2 Self-Healing Consumer")


def configured_api_key() -> str | None:
    return os.getenv("P2_API_KEY") or os.getenv("PLATFORM_API_KEY")


def require_api_key(x_api_key: str | None = Header(default=None)) -> None:
    expected_key = configured_api_key()
    if expected_key and x_api_key != expected_key:
        raise HTTPException(
            status_code=401,
            detail="cle API manquante ou invalide",
        )


@app.get("/", include_in_schema=False)
async def root():
    return RedirectResponse(url="/ui", status_code=302)


@app.get("/ui", response_class=HTMLResponse, include_in_schema=False)
async def ui():
    return HTMLResponse(render_dashboard_html())


@app.post("/events")
async def ingest_event(payload: Dict[str, Any], _: None = Depends(require_api_key)):
    inc_metric("p2_events_received_total")
    try:
        set_metric("p2_latest_risk_score", float(payload.get("risk_score", 0.0)))
    except (TypeError, ValueError):
        pass

    valid, reason = quick_validate(payload)
    if not valid:
        inc_metric("p2_events_rejected_total")
        raise HTTPException(status_code=400, detail={"validation_error": reason})

    # Log validation
    log(f"validated event_id={payload.get('event_id')} machine={payload.get('machine_id')} decision={payload.get('decision')} risk_score={payload.get('risk_score')}")

    kafka_config = load_kafka_config()
    kafka_result = {"published": False, "reason": "kafka_disabled"}
    if kafka_config.enabled:
        try:
            kafka_result = publish_event(
                payload,
                topic=kafka_config.input_topic,
                key=payload.get("correlation_id") or payload.get("event_id"),
            )
        except Exception as exc:
            raise HTTPException(
                status_code=503,
                detail={"broker_error": str(exc)},
            ) from exc

        # The Kafka worker owns execution in broker mode. Processing here as well
        # would create duplicate actuator commands and duplicate incidents.
        return {
            "status": "queued",
            "decision": payload.get("decision"),
            "kafka": kafka_result,
        }

    result = None
    if payload.get("decision") == "trigger_self_healing":
        inc_metric("p2_self_healing_triggered_total")
        result = simulate_playbook(payload)
        return {"status": "action_triggered", "result": result, "kafka": kafka_result}

    inc_metric("p2_no_action_total")
    return {"status": "no_action", "detail": "decision does not request self-healing", "kafka": kafka_result}


@app.get("/tickets")
async def tickets(limit: int = 50, status: str | None = None):
    return {"tickets": list_tickets(limit=limit, status=status)}


@app.get("/tickets/{ticket_id}")
async def ticket_detail(ticket_id: str):
    ticket = get_ticket(ticket_id)
    if ticket is None:
        raise HTTPException(status_code=404, detail="ticket introuvable")
    return ticket



@app.get("/health")
async def health():
    return {"status": "ok"}


@app.get("/metrics", response_class=PlainTextResponse)
async def metrics():
    return PlainTextResponse(
        render_prometheus_metrics(),
        media_type="text/plain; version=0.0.4; charset=utf-8",
    )
