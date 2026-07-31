import sys
from pathlib import Path

import pandas as pd


P1_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(P1_DIR))

from dashboard_analytics import (
    baseline_index,
    degradation_index,
    informative_sensors,
    normalized_trend,
    sensor_diagnostics,
)


def sample_frame():
    data = {"time_cycle": [1, 2, 3, 4]}
    for index in range(1, 22):
        data[f"sensor_{index}"] = [float(index)] * 4
    data["sensor_2"] = [10.0, 11.0, 12.0, 14.0]
    data["sensor_3"] = [100.0, 98.0, 95.0, 90.0]
    return pd.DataFrame(data)


def test_baseline_index_starts_at_100():
    result = baseline_index(sample_frame(), ["sensor_2", "sensor_3"])
    assert result.iloc[0].tolist() == [100.0, 100.0]
    assert result.iloc[-1]["sensor_2"] == 140.0


def test_normalized_trend_preserves_shape():
    result = normalized_trend(sample_frame(), ["sensor_2", "sensor_3"], window=2)
    assert result.shape == (4, 2)
    assert result.notna().all().all()


def test_diagnostics_identifies_directions():
    result = sensor_diagnostics(sample_frame(), ["sensor_2", "sensor_3"])
    directions = dict(zip(result["Capteur"], result["Tendance"]))
    assert directions == {"sensor_2": "hausse", "sensor_3": "baisse"}


def test_informative_sensors_excludes_constant_series():
    result = informative_sensors(sample_frame(), limit=4)
    assert "sensor_2" in result
    assert "sensor_3" in result
    assert "sensor_1" not in result


def test_degradation_index_is_bounded():
    result = degradation_index(sample_frame(), ["sensor_2", "sensor_3"], window=2)
    assert result.min() >= 0
    assert result.max() <= 100
