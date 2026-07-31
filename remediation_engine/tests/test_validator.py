import json
import sys
from pathlib import Path

# Ensure repo root is on sys.path for imports
ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(ROOT))

from remediation_engine.validator import validate_event_with_schema


BASE = Path(__file__).resolve().parent.parent


def load(name: str):
    return json.loads((BASE / "examples" / name).read_text())


def test_valid_event():
    ev = load("event_valid.json")
    ok, msg = validate_event_with_schema(ev)
    assert ok, msg


def test_invalid_event():
    ev = load("event_invalid.json")
    ok, msg = validate_event_with_schema(ev)
    assert not ok
