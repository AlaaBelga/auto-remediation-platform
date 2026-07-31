#!/usr/bin/env python3
"""Small dependency-free latency check for the P1 prediction endpoint."""

import argparse
import json
import os
import statistics
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
from urllib.request import Request, urlopen


BASE_DIR = Path(__file__).resolve().parent


def parse_args():
    parser = argparse.ArgumentParser(description="Measure P1 prediction latency")
    parser.add_argument("--url", default="http://127.0.0.1:8000/predict")
    parser.add_argument("--payload", default=str(BASE_DIR / "sample_payload.json"))
    parser.add_argument("--requests", type=int, default=100)
    parser.add_argument("--concurrency", type=int, default=5)
    parser.add_argument("--warmup", type=int, default=5)
    parser.add_argument(
        "--api-key",
        default=os.getenv("P1_API_KEY") or os.getenv("PLATFORM_API_KEY"),
        help="Cle API envoyee dans le header X-API-Key.",
    )
    return parser.parse_args()


def percentile(values, percentile_value):
    ordered = sorted(values)
    index = min(int(len(ordered) * percentile_value), len(ordered) - 1)
    return ordered[index]


def post(url, encoded_payload, api_key=None):
    headers = {"Content-Type": "application/json"}
    if api_key:
        headers["X-API-Key"] = api_key
    request = Request(
        url,
        data=encoded_payload,
        headers=headers,
        method="POST",
    )
    started = time.perf_counter()
    with urlopen(request, timeout=30) as response:
        response.read()
        status = response.status
    return status, (time.perf_counter() - started) * 1000


def main():
    args = parse_args()
    encoded_payload = Path(args.payload).read_bytes()

    for _ in range(args.warmup):
        post(args.url, encoded_payload, args.api_key)

    latencies = []
    failures = 0
    with ThreadPoolExecutor(max_workers=args.concurrency) as executor:
        futures = [
            executor.submit(post, args.url, encoded_payload)
            if args.api_key is None
            else executor.submit(post, args.url, encoded_payload, args.api_key)
            for _ in range(args.requests)
        ]
        for future in as_completed(futures):
            try:
                status, latency = future.result()
                if status == 200:
                    latencies.append(latency)
                else:
                    failures += 1
            except Exception:
                failures += 1

    if not latencies:
        raise SystemExit("Aucune requete reussie")

    result = {
        "requests": args.requests,
        "successful": len(latencies),
        "failures": failures,
        "concurrency": args.concurrency,
        "mean_ms": round(statistics.mean(latencies), 3),
        "p50_ms": round(percentile(latencies, 0.50), 3),
        "p95_ms": round(percentile(latencies, 0.95), 3),
        "max_ms": round(max(latencies), 3),
        "sla_p95_under_100_ms": percentile(latencies, 0.95) < 100,
    }
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
