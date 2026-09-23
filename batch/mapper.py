#!/usr/bin/env python3
"""Hadoop Streaming mapper: telemetry events to daily device aggregates."""

from __future__ import annotations

import json
import sys


def map_line(line: str) -> tuple[str, str]:
    event = json.loads(line)
    day = event["timestamp"][:10]
    key = f"{event['device_id']}|{day}"
    latency = float(event["latency_ms"])
    errors = float(event["error_rate"])
    return key, f"1,{latency},{latency * latency},{errors}"


def main() -> None:
    for line in sys.stdin:
        if line.strip():
            print(*map_line(line), sep="\t")


if __name__ == "__main__":
    main()

