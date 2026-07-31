#!/usr/bin/env python3
"""Replay NASA CMAPSS sensor rows to the console or Kafka."""

import argparse
import json
import time
from datetime import datetime, timezone
from pathlib import Path

import pandas as pd


BASE_DIR = Path(__file__).resolve().parent
DATA_PATH = BASE_DIR / "train_FD001.txt"
COLUMNS = (
    ["unit_number", "time_cycle"]
    + [f"op_setting_{i}" for i in range(1, 4)]
    + [f"sensor_{i}" for i in range(1, 22)]
)
FEATURES = [f"sensor_{i}" for i in range(1, 22)] + [
    f"op_setting_{i}" for i in range(1, 4)
]


def parse_args():
    parser = argparse.ArgumentParser(description="CMAPSS real-time stream simulator")
    parser.add_argument("--mode", choices=("console", "kafka"), default="console")
    parser.add_argument("--machine-id", type=int, default=1)
    parser.add_argument("--interval", type=float, default=1.0)
    parser.add_argument("--bootstrap-servers", default="127.0.0.1:29092")
    parser.add_argument("--topic", default="p1.sensor.readings")
    parser.add_argument("--loop", action="store_true")
    return parser.parse_args()


def load_machine(machine_id):
    frame = pd.read_csv(DATA_PATH, sep=r"\s+", header=None, names=COLUMNS)
    machine = frame[frame["unit_number"] == machine_id]
    if machine.empty:
        raise SystemExit(f"Machine {machine_id} absente du dataset")
    return machine


def build_event(row):
    payload = {feature: float(row[feature]) for feature in FEATURES}
    return {
        "event_type": "sensor_reading",
        "timestamp": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
        "machine_id": f"TURBINE_{int(row['unit_number']):03d}",
        "time_cycle": int(row["time_cycle"]),
        "payload": payload,
        "schema_version": "1.0",
    }


def make_producer(args):
    if args.mode != "kafka":
        return None
    try:
        from kafka import KafkaProducer
    except ImportError as exc:
        raise SystemExit(
            "Installez kafka-python avec: pip install kafka-python"
        ) from exc
    return KafkaProducer(
        bootstrap_servers=args.bootstrap_servers,
        value_serializer=lambda value: json.dumps(value).encode("utf-8"),
        retries=5,
    )


def main():
    args = parse_args()
    machine = load_machine(args.machine_id)
    producer = make_producer(args)

    try:
        while True:
            for _, row in machine.iterrows():
                event = build_event(row)
                if producer is None:
                    print(json.dumps(event, ensure_ascii=False))
                else:
                    metadata = producer.send(args.topic, event).get(timeout=10)
                    print(
                        f"published topic={metadata.topic} partition={metadata.partition} "
                        f"offset={metadata.offset} cycle={event['time_cycle']}"
                    )
                time.sleep(max(args.interval, 0))
            if not args.loop:
                break
    except KeyboardInterrupt:
        pass
    finally:
        if producer is not None:
            producer.flush()
            producer.close()


if __name__ == "__main__":
    main()
