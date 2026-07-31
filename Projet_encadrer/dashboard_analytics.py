"""Data transformations used by the Streamlit monitoring dashboard."""

import numpy as np
import pandas as pd


SENSOR_COLUMNS = [f"sensor_{i}" for i in range(1, 22)]


def informative_sensors(frame: pd.DataFrame, limit: int = 6) -> list[str]:
    """Rank sensors by absolute end-to-end change measured in standard deviations."""
    scores = {}
    for sensor in SENSOR_COLUMNS:
        series = frame[sensor].astype(float)
        standard_deviation = float(series.std())
        if standard_deviation <= 1e-12:
            continue
        scores[sensor] = abs(float(series.iloc[-1] - series.iloc[0])) / standard_deviation
    return sorted(scores, key=scores.get, reverse=True)[:limit]


def baseline_index(frame: pd.DataFrame, sensors: list[str]) -> pd.DataFrame:
    """Express every sensor as an index starting at 100."""
    values = frame[sensors].astype(float)
    baseline = values.iloc[0].replace(0, np.nan)
    indexed = values.divide(baseline).multiply(100)
    return indexed.replace([np.inf, -np.inf], np.nan).fillna(100.0)


def normalized_trend(
    frame: pd.DataFrame,
    sensors: list[str],
    window: int = 7,
) -> pd.DataFrame:
    """Return rolling z-scores so sensors with different units are comparable."""
    values = frame[sensors].astype(float)
    standard_deviation = values.std().replace(0, 1.0)
    normalized = (values - values.mean()) / standard_deviation
    return normalized.rolling(window=max(window, 1), min_periods=1).mean()


def sensor_diagnostics(frame: pd.DataFrame, sensors: list[str]) -> pd.DataFrame:
    """Summarize drift and variability for the selected machine."""
    rows = []
    cycles = frame["time_cycle"].astype(float).to_numpy()
    for sensor in sensors:
        values = frame[sensor].astype(float).to_numpy()
        slope = float(np.polyfit(cycles, values, 1)[0]) if len(values) > 1 else 0.0
        baseline = values[0]
        relative_change = (
            float((values[-1] - baseline) / abs(baseline) * 100)
            if abs(baseline) > 1e-12
            else 0.0
        )
        rows.append(
            {
                "Capteur": sensor,
                "Debut": round(float(values[0]), 4),
                "Fin": round(float(values[-1]), 4),
                "Variation (%)": round(relative_change, 3),
                "Pente / cycle": round(slope, 5),
                "Tendance": "hausse" if slope > 0 else "baisse" if slope < 0 else "stable",
            }
        )
    return pd.DataFrame(rows)


def degradation_index(frame: pd.DataFrame, sensors: list[str], window: int = 7) -> pd.Series:
    """Aggregate absolute normalized sensor drift into a readable health signal."""
    trends = normalized_trend(frame, sensors, window=window)
    baseline = trends.iloc[0]
    distance = (trends - baseline).abs().mean(axis=1)
    maximum = float(distance.max())
    if maximum <= 1e-12:
        return pd.Series(0.0, index=frame.index, name="indice_degradation")
    return distance.divide(maximum).multiply(100).rename("indice_degradation")
