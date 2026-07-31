import json
import os
import time
from pathlib import Path
from threading import Lock

import joblib
import pandas as pd
import sklearn
from fastapi import Depends, FastAPI, Header, HTTPException
from fastapi.responses import PlainTextResponse
from pydantic import BaseModel, ConfigDict


BASE_DIR = Path(__file__).resolve().parent
MODEL_PATH = Path(os.getenv("MODEL_PATH", BASE_DIR / "model.joblib"))
RUL_MODEL_PATH = Path(os.getenv("RUL_MODEL_PATH", BASE_DIR / "rul_model.joblib"))
ANOMALY_MODEL_PATH = Path(
    os.getenv("ANOMALY_MODEL_PATH", BASE_DIR / "anomaly_model.joblib")
)
FEATURES_PATH = Path(os.getenv("FEATURES_PATH", BASE_DIR / "model_features.joblib"))
FEATURE_PROFILE_PATH = Path(
    os.getenv("FEATURE_PROFILE_PATH", BASE_DIR / "feature_profile.joblib")
)
METADATA_PATH = Path(os.getenv("MODEL_METADATA_PATH", BASE_DIR / "model_metadata.json"))
MODEL_VERSION = os.getenv("MODEL_VERSION", "rf-1.2.0")
WARNING_THRESHOLD = float(os.getenv("RISK_WARNING_THRESHOLD", "0.60"))
CRITICAL_THRESHOLD = float(os.getenv("RISK_CRITICAL_THRESHOLD", "0.80"))


def load_model_metadata() -> dict:
    if not METADATA_PATH.exists():
        return {}
    return json.loads(METADATA_PATH.read_text())


def configured_api_key() -> str | None:
    return os.getenv("P1_API_KEY") or os.getenv("PLATFORM_API_KEY")


def require_api_key(x_api_key: str | None = Header(default=None)) -> None:
    expected_key = configured_api_key()
    if expected_key and x_api_key != expected_key:
        raise HTTPException(
            status_code=401,
            detail="cle API manquante ou invalide",
        )


model_metadata = load_model_metadata()
model = joblib.load(MODEL_PATH)
rul_model = joblib.load(RUL_MODEL_PATH)
anomaly_model = joblib.load(ANOMALY_MODEL_PATH)
features = joblib.load(FEATURES_PATH)
feature_profile = joblib.load(FEATURE_PROFILE_PATH)

app = FastAPI(
    title="Predictive Maintenance API",
    version=MODEL_VERSION,
    description="Prediction de risque de panne a partir des capteurs NASA CMAPSS.",
)

_metrics_lock = Lock()
_prediction_count = 0
_prediction_error_count = 0
_latest_risk_score = 0.0
_latest_latency_ms = 0.0


class SensorPayload(BaseModel):
    model_config = ConfigDict(extra="forbid")

    sensor_1: float
    sensor_2: float
    sensor_3: float
    sensor_4: float
    sensor_5: float
    sensor_6: float
    sensor_7: float
    sensor_8: float
    sensor_9: float
    sensor_10: float
    sensor_11: float
    sensor_12: float
    sensor_13: float
    sensor_14: float
    sensor_15: float
    sensor_16: float
    sensor_17: float
    sensor_18: float
    sensor_19: float
    sensor_20: float
    sensor_21: float
    op_setting_1: float
    op_setting_2: float
    op_setting_3: float

class PredictionResponse(BaseModel):
    prediction: int
    status: str
    risk_score: float
    rul_cycles: float
    estimated_time_to_failure_hours: float
    anomaly_detected: bool
    anomaly_score: float
    top_contributing_sensors: list[str]
    model_version: str
    prediction_time_ms: float


def classify_status(prediction: int, risk_score: float) -> str:
    if prediction == 1 or risk_score >= CRITICAL_THRESHOLD:
        return "CRITICAL"
    if risk_score >= WARNING_THRESHOLD:
        return "WARNING"
    return "OK"


def explain_prediction(values: dict[str, float], limit: int = 5) -> list[str]:
    contributions = {}
    for feature in features:
        if not feature.startswith("sensor_"):
            continue
        mean = float(feature_profile["means"][feature])
        standard_deviation = max(
            float(feature_profile["standard_deviations"][feature]),
            1e-12,
        )
        importance = float(feature_profile["importances"][feature])
        contributions[feature] = abs(values[feature] - mean) / standard_deviation * importance
    return sorted(contributions, key=contributions.get, reverse=True)[:limit]


@app.get("/")
def home():
    return {
        "message": "Predictive Maintenance API",
        "docs": "/docs",
        "health": "/health",
        "model_version": MODEL_VERSION,
    }


@app.get("/health")
def health():
    training_sklearn_version = model_metadata.get("scikit_learn_version")
    return {
        "status": "ok",
        "model_loaded": model is not None,
        "rul_model_loaded": rul_model is not None,
        "anomaly_model_loaded": anomaly_model is not None,
        "feature_count": len(features),
        "model_version": MODEL_VERSION,
        "scikit_learn_training_version": training_sklearn_version,
        "scikit_learn_runtime_version": sklearn.__version__,
        "model_runtime_compatible": (
            training_sklearn_version is None
            or training_sklearn_version == sklearn.__version__
        ),
    }


@app.post("/predict", response_model=PredictionResponse)
def predict(payload: SensorPayload, _: None = Depends(require_api_key)):
    global _prediction_count
    global _prediction_error_count
    global _latest_risk_score
    global _latest_latency_ms

    started = time.perf_counter()

    try:
        values = payload.model_dump()
        x = pd.DataFrame(
            [[values[feature] for feature in features]],
            columns=features,
        )
        if hasattr(model, "predict_proba"):
            risk_score = float(model.predict_proba(x)[0][1])
            prediction = int(risk_score >= 0.5)
        else:
            prediction = int(model.predict(x)[0])
            risk_score = float(prediction)

        rul_cycles = max(float(rul_model.predict(x)[0]), 0.0)
        anomaly_score = float(anomaly_model.decision_function(x)[0])
        anomaly_detected = anomaly_score < 0
        top_contributing_sensors = explain_prediction(values)

        latency_ms = (time.perf_counter() - started) * 1000
        status = classify_status(prediction, risk_score)

        with _metrics_lock:
            _prediction_count += 1
            _latest_risk_score = risk_score
            _latest_latency_ms = latency_ms

        return PredictionResponse(
            prediction=prediction,
            status=status,
            risk_score=risk_score,
            rul_cycles=round(rul_cycles, 2),
            estimated_time_to_failure_hours=round(rul_cycles, 2),
            anomaly_detected=anomaly_detected,
            anomaly_score=round(anomaly_score, 6),
            top_contributing_sensors=top_contributing_sensors,
            model_version=MODEL_VERSION,
            prediction_time_ms=round(latency_ms, 3),
        )
    except Exception:
        with _metrics_lock:
            _prediction_error_count += 1
        raise


@app.get("/metrics", response_class=PlainTextResponse)
def metrics():
    with _metrics_lock:
        body = "\n".join(
            [
                "# HELP p1_predictions_total Total predictions produced.",
                "# TYPE p1_predictions_total counter",
                f"p1_predictions_total {_prediction_count}",
                "# HELP p1_prediction_errors_total Total prediction errors.",
                "# TYPE p1_prediction_errors_total counter",
                f"p1_prediction_errors_total {_prediction_error_count}",
                "# HELP p1_latest_risk_score Latest predicted risk score.",
                "# TYPE p1_latest_risk_score gauge",
                f"p1_latest_risk_score {_latest_risk_score}",
                "# HELP p1_latest_prediction_latency_ms Latest prediction latency in milliseconds.",
                "# TYPE p1_latest_prediction_latency_ms gauge",
                f"p1_latest_prediction_latency_ms {_latest_latency_ms}",
                "",
            ]
        )
    return PlainTextResponse(body, media_type="text/plain; version=0.0.4")
