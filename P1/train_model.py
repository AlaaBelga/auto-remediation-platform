import json
from pathlib import Path

import joblib
import numpy as np
import pandas as pd
import sklearn
from sklearn.ensemble import IsolationForest, RandomForestClassifier, RandomForestRegressor
from sklearn.metrics import (
    classification_report,
    f1_score,
    mean_absolute_error,
    mean_squared_error,
    r2_score,
)
from sklearn.model_selection import GroupKFold, GroupShuffleSplit, cross_val_score


BASE_DIR = Path(__file__).resolve().parent
DATA_PATH = BASE_DIR / "train_FD001.txt"
MODEL_PATH = BASE_DIR / "model.joblib"
RUL_MODEL_PATH = BASE_DIR / "rul_model.joblib"
ANOMALY_MODEL_PATH = BASE_DIR / "anomaly_model.joblib"
FEATURES_PATH = BASE_DIR / "model_features.joblib"
FEATURE_PROFILE_PATH = BASE_DIR / "feature_profile.joblib"
METADATA_PATH = BASE_DIR / "model_metadata.json"
MODEL_VERSION = "rf-1.2.0"

COLUMNS = (
    ["unit_number", "time_cycle"]
    + [f"op_setting_{i}" for i in range(1, 4)]
    + [f"sensor_{i}" for i in range(1, 22)]
)

FEATURES = [f"sensor_{i}" for i in range(1, 22)] + [
    f"op_setting_{i}" for i in range(1, 4)
]


def load_training_data():
    df = pd.read_csv(DATA_PATH, sep=r"\s+", header=None, names=COLUMNS)
    max_cycle = df.groupby("unit_number")["time_cycle"].transform("max")
    df["RUL"] = max_cycle - df["time_cycle"]
    df["failure_label"] = (df["RUL"] <= 30).astype(int)
    return df


def split_by_machine(df):
    first_split = GroupShuffleSplit(
        n_splits=1,
        train_size=0.70,
        random_state=42,
    )
    train_index, temporary_index = next(
        first_split.split(df, groups=df["unit_number"])
    )

    train_df = df.iloc[train_index].copy()
    temporary_df = df.iloc[temporary_index].copy()

    second_split = GroupShuffleSplit(
        n_splits=1,
        train_size=0.50,
        random_state=42,
    )
    validation_index, test_index = next(
        second_split.split(
            temporary_df,
            groups=temporary_df["unit_number"],
        )
    )

    return (
        train_df,
        temporary_df.iloc[validation_index].copy(),
        temporary_df.iloc[test_index].copy(),
    )


def evaluate(model, frame, label):
    predictions = model.predict(frame[FEATURES])
    score = f1_score(frame["failure_label"], predictions)
    print(f"\n{label} F1-score: {score:.4f}")
    print(classification_report(frame["failure_label"], predictions))
    return float(score)


def evaluate_rul(model, frame, label):
    predictions = np.maximum(model.predict(frame[FEATURES]), 0)
    actual = frame["RUL"]
    metrics = {
        "mae": float(mean_absolute_error(actual, predictions)),
        "rmse": float(np.sqrt(mean_squared_error(actual, predictions))),
        "r2": float(r2_score(actual, predictions)),
    }
    print(
        f"{label} RUL: MAE={metrics['mae']:.2f}, "
        f"RMSE={metrics['rmse']:.2f}, R2={metrics['r2']:.4f}"
    )
    return metrics


def build_feature_profile(train_df, classifier):
    means = train_df[FEATURES].mean()
    standard_deviations = train_df[FEATURES].std().replace(0, 1.0)
    importances = pd.Series(classifier.feature_importances_, index=FEATURES)
    return {
        "means": means.to_dict(),
        "standard_deviations": standard_deviations.to_dict(),
        "importances": importances.to_dict(),
    }


def main():
    df = load_training_data()
    train_df, validation_df, test_df = split_by_machine(df)

    print("Machines par split :")
    print(
        {
            "train": train_df["unit_number"].nunique(),
            "validation": validation_df["unit_number"].nunique(),
            "test": test_df["unit_number"].nunique(),
        }
    )

    classifier = RandomForestClassifier(
        n_estimators=50,
        random_state=42,
        class_weight="balanced",
        n_jobs=1,
    )

    group_cv = GroupKFold(n_splits=5)
    cv_scores = cross_val_score(
        classifier,
        train_df[FEATURES],
        train_df["failure_label"],
        groups=train_df["unit_number"],
        cv=group_cv,
        scoring="f1",
        n_jobs=1,
    )
    print(f"GroupKFold F1: {cv_scores.mean():.4f} +/- {cv_scores.std():.4f}")

    classifier.fit(train_df[FEATURES], train_df["failure_label"])
    validation_f1 = evaluate(classifier, validation_df, "Validation")
    test_f1 = evaluate(classifier, test_df, "Test")

    rul_model = RandomForestRegressor(
        n_estimators=30,
        random_state=42,
        min_samples_leaf=2,
        n_jobs=1,
    )
    rul_model.fit(train_df[FEATURES], train_df["RUL"])
    validation_rul = evaluate_rul(rul_model, validation_df, "Validation")
    test_rul = evaluate_rul(rul_model, test_df, "Test")

    healthy_training_rows = train_df[train_df["RUL"] > 30]
    anomaly_model = IsolationForest(
        n_estimators=20,
        contamination=0.03,
        random_state=42,
        n_jobs=1,
    )
    anomaly_model.fit(healthy_training_rows[FEATURES])

    feature_profile = build_feature_profile(train_df, classifier)

    joblib.dump(classifier, MODEL_PATH)
    joblib.dump(rul_model, RUL_MODEL_PATH)
    joblib.dump(anomaly_model, ANOMALY_MODEL_PATH)
    joblib.dump(FEATURES, FEATURES_PATH)
    joblib.dump(feature_profile, FEATURE_PROFILE_PATH)

    metadata = {
        "model_version": MODEL_VERSION,
        "scikit_learn_version": sklearn.__version__,
        "pandas_version": pd.__version__,
        "numpy_version": np.__version__,
        "joblib_version": joblib.__version__,
        "classification_algorithm": "RandomForestClassifier",
        "rul_algorithm": "RandomForestRegressor",
        "anomaly_algorithm": "IsolationForest",
        "failure_threshold_rul_cycles": 30,
        "split_strategy": "grouped by unit_number (70/15/15)",
        "group_kfold_f1_mean": float(cv_scores.mean()),
        "group_kfold_f1_std": float(cv_scores.std()),
        "validation_f1": validation_f1,
        "test_f1": test_f1,
        "validation_rul": validation_rul,
        "test_rul": test_rul,
        "anomaly_training_rows": int(len(healthy_training_rows)),
        "anomaly_contamination": 0.03,
        "feature_count": len(FEATURES),
    }
    METADATA_PATH.write_text(json.dumps(metadata, indent=2))

    print(f"Modele classification sauvegarde : {MODEL_PATH}")
    print(f"Modele RUL sauvegarde : {RUL_MODEL_PATH}")
    print(f"Modele anomalie sauvegarde : {ANOMALY_MODEL_PATH}")
    print(f"Metadonnees sauvegardees : {METADATA_PATH}")


if __name__ == "__main__":
    main()
