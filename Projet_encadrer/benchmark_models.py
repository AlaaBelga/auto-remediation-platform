#!/usr/bin/env python3
"""Measure warm single-row inference time for each P1 model."""

import json
import time
from pathlib import Path

import joblib
import pandas as pd


BASE_DIR = Path(__file__).resolve().parent


def elapsed_ms(callback, repetitions=20):
    started = time.perf_counter()
    for _ in range(repetitions):
        callback()
    return (time.perf_counter() - started) * 1000 / repetitions


def main():
    features = joblib.load(BASE_DIR / "model_features.joblib")
    payload = json.loads((BASE_DIR / "sample_payload.json").read_text())
    frame = pd.DataFrame(
        [[payload[feature] for feature in features]],
        columns=features,
    )
    models = {
        "classification": joblib.load(BASE_DIR / "model.joblib"),
        "rul": joblib.load(BASE_DIR / "rul_model.joblib"),
        "anomaly": joblib.load(BASE_DIR / "anomaly_model.joblib"),
    }

    results = {}
    for name, model in models.items():
        model.predict(frame)
        results[name] = round(elapsed_ms(lambda: model.predict(frame)), 3)
    print(json.dumps(results, indent=2))


if __name__ == "__main__":
    main()
