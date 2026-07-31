import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(ROOT))

from P2.p1_to_p2_bridge import build_p2_event, classify_prediction
from P2.validator import validate_event_with_schema


def test_build_p2_event_from_critical_p1_prediction():
    event = build_p2_event(
        prediction_response={
            "prediction": 1,
            "status": "RISQUE_DE_PANNE",
            "risk_score": 0.91,
        },
        machine_id="unit_42",
        correlation_id="corr-test",
        api_latency_ms=42,
    )

    assert event["event_type"] == "machine_risk_assessed"
    assert event["source"] == "pilier_1"
    assert event["machine_id"] == "unit_42"
    assert event["decision"] == "trigger_self_healing"
    assert event["severity"] == "high"
    assert event["recommended_action"] == "restart_service"
    assert "prediction_equals_failure" in event["reason"]

    ok, reason = validate_event_with_schema(event)
    assert ok, reason


def test_classify_prediction_warning_escalates_without_self_healing():
    policy = classify_prediction(
        prediction=0,
        risk_score=0.65,
        warning_threshold=0.60,
        critical_threshold=0.80,
    )

    assert policy["decision"] == "escalate"
    assert policy["severity"] == "medium"
    assert policy["recommended_action"] == "notify_maintainer"


def test_bridge_uses_model_version_returned_by_p1():
    event = build_p2_event(
        prediction_response={
            "prediction": 0,
            "status": "OK",
            "risk_score": 0.12,
            "model_version": "rf-1.2.0",
        },
        machine_id="unit_7",
    )
    assert event["model_version"] == "rf-1.2.0"


def test_bridge_forwards_ml_context_fields():
    event = build_p2_event(
        prediction_response={
            "prediction": 1,
            "status": "CRITICAL",
            "risk_score": 0.97,
            "estimated_time_to_failure_hours": 7.5,
            "anomaly_detected": True,
            "anomaly_score": -0.42,
            "top_contributing_sensors": ["sensor_11", "sensor_4"],
        },
        machine_id="unit_9",
    )

    assert event["estimated_time_to_failure_hours"] == 7.5
    assert event["anomaly_detected"] is True
    assert event["top_contributing_sensors"] == ["sensor_11", "sensor_4"]
