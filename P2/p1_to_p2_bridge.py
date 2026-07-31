#!/usr/bin/env python3
"""Bridge a Pilier 1 prediction into the Pilier 2 event contract.

The script calls P1 /predict with a sensor payload, converts the prediction response
to the strict P1 -> P2 event schema, then posts that event to P2 /events.
"""
import argparse
import json
import os
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Optional
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen
from uuid import uuid4


DEFAULT_P1_URL = "http://127.0.0.1:8000/predict"
DEFAULT_P2_URL = "http://127.0.0.1:8001/events"
DEFAULT_WARNING_THRESHOLD = 0.60
DEFAULT_CRITICAL_THRESHOLD = 0.80
SCHEMA_VERSION = "1.0"


class BridgeError(RuntimeError):
    """Raised when the bridge cannot complete one step of the handoff."""


def utc_timestamp() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def make_event_id(now: Optional[datetime] = None) -> str:
    now = now or datetime.now(timezone.utc)
    return f"evt-{now.strftime('%Y%m%d')}-{uuid4().hex[:12]}"


def post_json(
    url: str,
    payload: Dict[str, Any],
    timeout: float,
    api_key: Optional[str] = None,
) -> Dict[str, Any]:
    body = json.dumps(payload).encode("utf-8")
    headers = {"Content-Type": "application/json"}
    if api_key:
        headers["X-API-Key"] = api_key
    request = Request(
        url,
        data=body,
        headers=headers,
        method="POST",
    )

    try:
        with urlopen(request, timeout=timeout) as response:
            response_body = response.read().decode("utf-8")
            return json.loads(response_body) if response_body else {}
    except HTTPError as exc:
        detail = exc.read().decode("utf-8", errors="replace")
        raise BridgeError(f"HTTP {exc.code} from {url}: {detail}") from exc
    except URLError as exc:
        raise BridgeError(f"Cannot reach {url}: {exc.reason}") from exc
    except json.JSONDecodeError as exc:
        raise BridgeError(f"Invalid JSON response from {url}") from exc


def load_payload(path: str) -> Dict[str, Any]:
    try:
        payload = json.loads(Path(path).read_text())
    except json.JSONDecodeError as exc:
        raise BridgeError(f"Invalid JSON payload file: {path}") from exc

    if not isinstance(payload, dict):
        raise BridgeError("Payload file must contain a JSON object")
    return payload


def classify_prediction(
    prediction: int,
    risk_score: float,
    warning_threshold: float,
    critical_threshold: float,
) -> Dict[str, Any]:
    reasons = []
    if prediction == 1:
        reasons.append("prediction_equals_failure")
    if risk_score >= critical_threshold:
        reasons.append("risk_score_above_critical_threshold")
    elif risk_score >= warning_threshold:
        reasons.append("risk_score_above_warning_threshold")

    if prediction == 1 or risk_score >= critical_threshold:
        return {
            "decision": "trigger_self_healing",
            "severity": "high",
            "recommended_action": "restart_service",
            "reasons": reasons or ["critical_policy_matched"],
        }

    if risk_score >= warning_threshold:
        return {
            "decision": "escalate",
            "severity": "medium",
            "recommended_action": "notify_maintainer",
            "reasons": reasons,
        }

    return {
        "decision": "observe",
        "severity": "low",
        "recommended_action": "no_action",
        "reasons": reasons or ["risk_score_below_warning_threshold"],
    }


def build_p2_event(
    prediction_response: Dict[str, Any],
    machine_id: str,
    correlation_id: Optional[str] = None,
    model_version: Optional[str] = None,
    warning_threshold: float = DEFAULT_WARNING_THRESHOLD,
    critical_threshold: float = DEFAULT_CRITICAL_THRESHOLD,
    api_latency_ms: Optional[int] = None,
) -> Dict[str, Any]:
    if "error" in prediction_response:
        raise BridgeError(f"P1 prediction returned an error: {prediction_response['error']}")

    try:
        prediction = int(prediction_response["prediction"])
        risk_score = float(prediction_response["risk_score"])
    except KeyError as exc:
        raise BridgeError(f"P1 response is missing required field: {exc.args[0]}") from exc
    except (TypeError, ValueError) as exc:
        raise BridgeError("P1 response contains invalid prediction or risk_score") from exc

    policy = classify_prediction(
        prediction=prediction,
        risk_score=risk_score,
        warning_threshold=warning_threshold,
        critical_threshold=critical_threshold,
    )

    event = {
        "event_id": make_event_id(),
        "event_type": "machine_risk_assessed",
        "timestamp": utc_timestamp(),
        "source": "pilier_1",
        "correlation_id": correlation_id or f"corr-{uuid4().hex[:12]}",
        "machine_id": machine_id,
        "prediction": prediction,
        "status": str(prediction_response.get("status") or ("RISQUE_DE_PANNE" if prediction == 1 else "OK")),
        "risk_score": risk_score,
        "threshold": critical_threshold,
        "decision": policy["decision"],
        "model_version": model_version
        or str(prediction_response.get("model_version", "unknown")),
        "confidence": risk_score,
        "severity": policy["severity"],
        "recommended_action": policy["recommended_action"],
        "reason": policy["reasons"],
        "schema_version": SCHEMA_VERSION,
    }

    if api_latency_ms is not None:
        event["api_latency_ms"] = api_latency_ms

    optional_fields = [
        "estimated_time_to_failure_hours",
        "anomaly_detected",
        "anomaly_score",
        "top_contributing_sensors",
        "service_health_ok",
    ]
    for field in optional_fields:
        if field in prediction_response:
            event[field] = prediction_response[field]

    return event


def run_bridge(args: argparse.Namespace) -> Dict[str, Any]:
    payload = load_payload(args.payload_file)

    started = time.perf_counter()
    p1_api_key = args.p1_api_key or os.getenv("P1_API_KEY") or os.getenv("PLATFORM_API_KEY")
    p2_api_key = args.p2_api_key or os.getenv("P2_API_KEY") or os.getenv("PLATFORM_API_KEY")

    prediction_response = post_json(
        args.p1_url,
        payload,
        timeout=args.timeout,
        api_key=p1_api_key,
    )
    latency_ms = int((time.perf_counter() - started) * 1000)

    event = build_p2_event(
        prediction_response=prediction_response,
        machine_id=args.machine_id,
        correlation_id=args.correlation_id,
        model_version=args.model_version,
        warning_threshold=args.warning_threshold,
        critical_threshold=args.critical_threshold,
        api_latency_ms=latency_ms,
    )

    if args.dry_run:
        return {"prediction": prediction_response, "event": event, "p2_response": None}

    p2_response = post_json(
        args.p2_url,
        event,
        timeout=args.timeout,
        api_key=p2_api_key,
    )
    return {"prediction": prediction_response, "event": event, "p2_response": p2_response}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Call P1 /predict and forward a valid event to P2 /events.")
    parser.add_argument("--payload-file", required=True, help="JSON file containing the flat P1 sensor payload.")
    parser.add_argument("--machine-id", required=True, help="Machine identifier to place in the P2 event.")
    parser.add_argument("--p1-url", default=DEFAULT_P1_URL, help=f"P1 prediction URL. Default: {DEFAULT_P1_URL}")
    parser.add_argument("--p2-url", default=DEFAULT_P2_URL, help=f"P2 events URL. Default: {DEFAULT_P2_URL}")
    parser.add_argument("--correlation-id", help="Optional correlation id. Generated when omitted.")
    parser.add_argument(
        "--model-version",
        help="Optional override. By default the bridge uses the version returned by P1.",
    )
    parser.add_argument("--warning-threshold", type=float, default=DEFAULT_WARNING_THRESHOLD)
    parser.add_argument("--critical-threshold", type=float, default=DEFAULT_CRITICAL_THRESHOLD)
    parser.add_argument("--p1-api-key", help="Cle API a envoyer a P1. Par defaut: P1_API_KEY ou PLATFORM_API_KEY.")
    parser.add_argument("--p2-api-key", help="Cle API a envoyer a P2. Par defaut: P2_API_KEY ou PLATFORM_API_KEY.")
    parser.add_argument("--timeout", type=float, default=10.0)
    parser.add_argument("--dry-run", action="store_true", help="Build and print the event without posting to P2.")
    return parser.parse_args()


def main() -> None:
    try:
        result = run_bridge(parse_args())
    except BridgeError as exc:
        raise SystemExit(str(exc)) from exc

    print(json.dumps(result, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
