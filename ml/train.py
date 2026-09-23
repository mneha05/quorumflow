"""Train a small TensorFlow autoencoder for telemetry anomaly scoring."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

import numpy as np
import tensorflow as tf


FEATURES = ["cpu", "memory", "latency_ms", "error_rate"]


def make_dataset(rows: int, seed: int) -> tuple[np.ndarray, np.ndarray]:
    rng = np.random.default_rng(seed)
    normal = np.column_stack(
        [
            rng.normal(0.48, 0.10, rows),
            rng.normal(0.57, 0.09, rows),
            rng.lognormal(3.4, 0.22, rows),
            rng.beta(1.5, 80.0, rows),
        ]
    ).astype(np.float32)
    anomalies = normal.copy()
    anomaly_mask = rng.random(rows) < 0.08
    anomalies[anomaly_mask, 0] += rng.uniform(0.35, 0.7, anomaly_mask.sum())
    anomalies[anomaly_mask, 2] *= rng.uniform(2.5, 6.0, anomaly_mask.sum())
    anomalies[anomaly_mask, 3] += rng.uniform(0.08, 0.3, anomaly_mask.sum())
    return anomalies, anomaly_mask.astype(np.float32)


def build_model(width: int) -> tf.keras.Model:
    inputs = tf.keras.Input(shape=(width,), name="telemetry")
    x = tf.keras.layers.Dense(16, activation="relu")(inputs)
    x = tf.keras.layers.Dense(4, activation="relu", name="bottleneck")(x)
    x = tf.keras.layers.Dense(16, activation="relu")(x)
    outputs = tf.keras.layers.Dense(width, name="reconstruction")(x)
    model = tf.keras.Model(inputs, outputs, name="quorumflow_autoencoder")
    model.compile(optimizer="adam", loss="mse")
    return model


def train(rows: int, epochs: int, output: Path) -> dict[str, float | int]:
    tf.keras.utils.set_random_seed(7)
    values, labels = make_dataset(rows, seed=7)
    train_values = values[labels == 0]
    mean = train_values.mean(axis=0)
    scale = train_values.std(axis=0) + 1e-6
    normalized = (train_values - mean) / scale

    model = build_model(len(FEATURES))
    history = model.fit(
        normalized,
        normalized,
        validation_split=0.15,
        epochs=epochs,
        batch_size=64,
        verbose=0,
    )
    output.mkdir(parents=True, exist_ok=True)
    model.save(output / "model.keras")

    all_normalized = (values - mean) / scale
    reconstruction = model.predict(all_normalized, verbose=0)
    scores = np.mean(np.square(all_normalized - reconstruction), axis=1)
    threshold = float(np.percentile(scores[labels == 0], 99))
    auc = tf.keras.metrics.AUC()
    auc.update_state(labels, scores)
    metadata = {
        "rows": rows,
        "epochs": epochs,
        "features": FEATURES,
        "mean": mean.tolist(),
        "scale": scale.tolist(),
        "threshold": threshold,
        "auc": float(auc.result()),
        "final_val_loss": float(history.history["val_loss"][-1]),
    }
    (output / "metadata.json").write_text(json.dumps(metadata, indent=2) + "\n")
    return {key: metadata[key] for key in ("rows", "epochs", "threshold", "auc", "final_val_loss")}


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--rows", type=int, default=4_000)
    parser.add_argument("--epochs", type=int, default=8)
    parser.add_argument("--output", type=Path, default=Path("artifacts/tensorflow"))
    args = parser.parse_args()
    print(json.dumps(train(args.rows, args.epochs, args.output), indent=2))


if __name__ == "__main__":
    main()

