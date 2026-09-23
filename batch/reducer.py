#!/usr/bin/env python3
"""Hadoop Streaming reducer: merge daily telemetry statistics."""

from __future__ import annotations

import json
import math
import sys


def emit(key: str, count: int, total: float, square_total: float, errors: float) -> None:
    device_id, day = key.split("|", 1)
    mean = total / count
    variance = max(square_total / count - mean * mean, 0.0)
    print(
        json.dumps(
            {
                "device_id": device_id,
                "day": day,
                "events": count,
                "latency_mean_ms": round(mean, 6),
                "latency_stddev_ms": round(math.sqrt(variance), 6),
                "error_rate_mean": round(errors / count, 8),
            },
            separators=(",", ":"),
        )
    )


def main() -> None:
    current = None
    count = 0
    total = square_total = errors = 0.0
    for line in sys.stdin:
        key, values = line.rstrip().split("\t", 1)
        if current is not None and key != current:
            emit(current, count, total, square_total, errors)
            count = 0
            total = square_total = errors = 0.0
        current = key
        row_count, row_total, row_squares, row_errors = values.split(",")
        count += int(row_count)
        total += float(row_total)
        square_total += float(row_squares)
        errors += float(row_errors)
    if current is not None:
        emit(current, count, total, square_total, errors)


if __name__ == "__main__":
    main()

