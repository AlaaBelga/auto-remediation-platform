#!/usr/bin/env python3
"""Generate reproducible figures and tables for the Data Science report."""

import json
import os
from pathlib import Path

import joblib
import pandas as pd


BASE_DIR = Path(__file__).resolve().parent
OUTPUT_DIR = BASE_DIR / "report_assets"
os.environ.setdefault("MPLCONFIGDIR", str(BASE_DIR / ".matplotlib"))

import matplotlib.pyplot as plt


def save_feature_importance():
    profile = joblib.load(BASE_DIR / "feature_profile.joblib")
    importance = (
        pd.Series(profile["importances"], name="importance")
        .sort_values(ascending=False)
        .rename_axis("feature")
        .reset_index()
    )
    importance.to_csv(OUTPUT_DIR / "feature_importance.csv", index=False)

    top = importance.head(12).sort_values("importance")
    figure, axis = plt.subplots(figsize=(9, 6))
    axis.barh(top["feature"], top["importance"], color="#1976d2")
    axis.set_title("Top 12 des variables du modele de classification")
    axis.set_xlabel("Importance Random Forest")
    axis.grid(axis="x", alpha=0.25)
    figure.tight_layout()
    figure.savefig(OUTPUT_DIR / "feature_importance.png", dpi=180)
    plt.close(figure)


def save_model_metrics():
    metadata = json.loads((BASE_DIR / "model_metadata.json").read_text())
    rows = [
        {"metrique": "F1 validation", "valeur": metadata["validation_f1"]},
        {"metrique": "F1 test", "valeur": metadata["test_f1"]},
        {"metrique": "RUL MAE test", "valeur": metadata["test_rul"]["mae"]},
        {"metrique": "RUL RMSE test", "valeur": metadata["test_rul"]["rmse"]},
        {"metrique": "RUL R2 test", "valeur": metadata["test_rul"]["r2"]},
    ]
    pd.DataFrame(rows).to_csv(OUTPUT_DIR / "model_metrics.csv", index=False)


def main():
    OUTPUT_DIR.mkdir(exist_ok=True)
    save_feature_importance()
    save_model_metrics()
    print(f"Assets du rapport crees dans {OUTPUT_DIR}")


if __name__ == "__main__":
    main()
