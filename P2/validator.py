import json
from pathlib import Path
from jsonschema import Draft7Validator, exceptions

BASE = Path(__file__).resolve().parent
SCHEMA_FILE = BASE / "P1_to_P2_event_schema_v1.json"


def load_schema():
    with open(SCHEMA_FILE, "r") as f:
        return json.load(f)


SCHEMA = load_schema()
VALIDATOR = Draft7Validator(SCHEMA)


def validate_event_with_schema(event: dict):
    """Validate using jsonschema Draft7Validator. Returns (True, 'ok') or (False, message)."""
    errors = sorted(VALIDATOR.iter_errors(event), key=lambda e: e.path)
    if errors:
        msgs = []
        for e in errors:
            path = ".".join([str(p) for p in e.path]) or "<root>"
            msgs.append(f"{path}: {e.message}")
        return False, "; ".join(msgs)
    return True, "ok"


def quick_validate(event: dict):
    # wrapper for compatibility with previous code
    return validate_event_with_schema(event)
