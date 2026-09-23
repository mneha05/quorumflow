from __future__ import annotations

import json
import subprocess
import sys
import unittest
from pathlib import Path


ROOT = Path(__file__).parents[1]


class HadoopStreamingContractTests(unittest.TestCase):
    def test_mapper_and_reducer_emit_daily_device_baselines(self) -> None:
        telemetry = (ROOT / "samples" / "telemetry.jsonl").read_text()
        mapped = subprocess.run(
            [sys.executable, "batch/mapper.py"],
            cwd=ROOT,
            input=telemetry,
            text=True,
            capture_output=True,
            check=True,
        ).stdout
        reduced = subprocess.run(
            [sys.executable, "batch/reducer.py"],
            cwd=ROOT,
            input="".join(sorted(mapped.splitlines(keepends=True))),
            text=True,
            capture_output=True,
            check=True,
        ).stdout

        rows = [json.loads(line) for line in reduced.splitlines()]
        self.assertEqual([row["device_id"] for row in rows], ["edge-04", "edge-17"])
        self.assertEqual([row["events"] for row in rows], [3, 3])
        self.assertAlmostEqual(rows[0]["latency_mean_ms"], 29.533333)
        self.assertAlmostEqual(rows[1]["error_rate_mean"], 0.04066667)


if __name__ == "__main__":
    unittest.main()
