"""Score JSON-lines feature windows with an exported TensorFlow model."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import numpy as np
import tensorflow as tf


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--model-dir", type=Path, default=Path("artifacts/tensorflow"))
    args = parser.parse_args()
    metadata = json.loads((args.model_dir / "metadata.json").read_text())
    model = tf.keras.models.load_model(args.model_dir / "model.keras")
    mean = np.asarray(metadata["mean"], dtype=np.float32)
    scale = np.asarray(metadata["scale"], dtype=np.float32)

    for line in sys.stdin:
        event = json.loads(line)
        values = np.asarray([[event[name] for name in metadata["features"]]], dtype=np.float32)
        normalized = (values - mean) / scale
        reconstructed = model(normalized, training=False).numpy()
        score = float(np.mean(np.square(normalized - reconstructed)))
        event["anomaly_score"] = score
        event["anomaly"] = score >= metadata["threshold"]
        print(json.dumps(event, separators=(",", ":")))


if __name__ == "__main__":
    main()

