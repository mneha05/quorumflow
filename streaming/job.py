"""Apache Flink event-time feature pipeline for QuorumFlow telemetry."""

from __future__ import annotations

import argparse
import json
from datetime import datetime

from pyflink.common import Duration, Encoder, Types, WatermarkStrategy
from pyflink.common.time import Time
from pyflink.datastream import StreamExecutionEnvironment
from pyflink.datastream.connectors.file_system import FileSink
from pyflink.datastream.functions import ProcessWindowFunction, RuntimeContext
from pyflink.datastream.window import TumblingEventTimeWindows


def parse_event(line: str) -> dict[str, object]:
    event = json.loads(line)
    event["event_time_ms"] = int(datetime.fromisoformat(event["timestamp"].replace("Z", "+00:00")).timestamp() * 1000)
    return event


class EventTimestamp:
    def extract_timestamp(self, value: dict[str, object], record_timestamp: int) -> int:
        return int(value["event_time_ms"])


class FeatureWindow(ProcessWindowFunction):
    def process(self, key: str, context, elements):
        rows = list(elements)
        count = len(rows)
        yield json.dumps(
            {
                "device_id": key,
                "window_start_ms": context.window().start,
                "window_end_ms": context.window().end,
                "cpu": sum(float(row["cpu"]) for row in rows) / count,
                "memory": sum(float(row["memory"]) for row in rows) / count,
                "latency_ms": sum(float(row["latency_ms"]) for row in rows) / count,
                "error_rate": sum(float(row["error_rate"]) for row in rows) / count,
                "events": count,
            },
            separators=(",", ":"),
        )


def build_job(input_path: str, output_path: str) -> None:
    env = StreamExecutionEnvironment.get_execution_environment()
    env.enable_checkpointing(10_000)
    lines = env.read_text_file(input_path)
    events = lines.map(parse_event, output_type=Types.PICKLED_BYTE_ARRAY())
    watermarked = events.assign_timestamps_and_watermarks(
        WatermarkStrategy.for_bounded_out_of_orderness(Duration.of_seconds(5))
        .with_timestamp_assigner(EventTimestamp())
    )
    features = (
        watermarked.key_by(lambda row: str(row["device_id"]))
        .window(TumblingEventTimeWindows.of(Time.seconds(30)))
        .process(FeatureWindow(), output_type=Types.STRING())
    )
    sink = FileSink.for_row_format(output_path, Encoder.simple_string_encoder()).build()
    features.sink_to(sink)
    env.execute("quorumflow-event-time-features")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", default="samples/telemetry.jsonl")
    parser.add_argument("--output", default="artifacts/flink-features")
    args = parser.parse_args()
    build_job(args.input, args.output)


if __name__ == "__main__":
    main()

