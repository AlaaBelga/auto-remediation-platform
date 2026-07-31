import json
import sys
from pathlib import Path

from fastapi.testclient import TestClient


P1_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(P1_DIR))

from api import app


client = TestClient(app)


def load_payload(name: str):
    return json.loads((P1_DIR / name).read_text())


def test_health_reports_loaded_model():
    response = client.get("/health")
    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "ok"
    assert body["model_loaded"] is True
    assert body["rul_model_loaded"] is True
    assert body["anomaly_model_loaded"] is True
    assert body["feature_count"] == 24


def test_predict_returns_contract():
    response = client.post("/predict", json=load_payload("sample_payload.json"))
    assert response.status_code == 200
    body = response.json()
    assert body["prediction"] in (0, 1)
    assert body["status"] in {"OK", "WARNING", "CRITICAL"}
    assert 0.0 <= body["risk_score"] <= 1.0
    assert body["rul_cycles"] >= 0
    assert body["estimated_time_to_failure_hours"] >= 0
    assert isinstance(body["anomaly_detected"], bool)
    assert isinstance(body["anomaly_score"], float)
    assert 1 <= len(body["top_contributing_sensors"]) <= 5
    assert all(name.startswith("sensor_") for name in body["top_contributing_sensors"])
    assert body["model_version"]
    assert body["prediction_time_ms"] >= 0


def test_predict_rejects_missing_features():
    response = client.post("/predict", json={"sensor_1": 1.0})
    assert response.status_code == 422


def test_predict_requires_api_key_when_configured(monkeypatch):
    monkeypatch.setenv("P1_API_KEY", "secret-test-key")
    payload = load_payload("sample_payload.json")

    missing_key_response = client.post("/predict", json=payload)
    assert missing_key_response.status_code == 401

    valid_key_response = client.post(
        "/predict",
        json=payload,
        headers={"X-API-Key": "secret-test-key"},
    )
    assert valid_key_response.status_code == 200


def test_metrics_exposes_prediction_metrics():
    client.post("/predict", json=load_payload("sample_payload.json"))
    response = client.get("/metrics")
    assert response.status_code == 200
    assert "p1_predictions_total" in response.text
    assert "p1_latest_prediction_latency_ms" in response.text
