#!/usr/bin/env python3
"""Run training for MLP detector and LSTM language model."""

import logging
import time
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(message)s",
)

from texthumanize.training import Trainer

def main():
    t0 = time.time()
    trainer = Trainer(seed=42)

    # 1. Generate training data
    print("=== Generating training data ===")
    data_stats = trainer.generate_data(n_samples=500, val_split=0.2)
    print(f"Data: {data_stats}")
    print(f"Time: {time.time()-t0:.1f}s")

    # 2. Train MLP detector
    print()
    print("=== Training MLP detector ===")
    t1 = time.time()
    result = trainer.train_detector(epochs=20, lr=0.002, verbose=True)
    print(f"Epochs: {result['epochs_trained']}")
    print(f"Best val acc: {result['best_val_accuracy']:.4f}")
    print(f"Final metrics: {result['final_metrics']}")
    print(f"Params: {result['param_count']}")
    print(f"Time: {time.time()-t1:.1f}s")

    for e in result["training_log"][-5:]:
        print(f"  Epoch {e['epoch']}: loss={e['train_loss']:.4f} acc={e['val_accuracy']:.4f} f1={e['val_f1']:.4f}")

    # 3. Export detector weights
    print()
    print("=== Exporting detector weights ===")
    exported = trainer.export_weights("texthumanize/weights")
    for name, path in exported.items():
        size = os.path.getsize(path)
        print(f"  {name}: {path} ({size} bytes)")

    # 4. Train LSTM LM (minimal — pure Python BPTT is slow)
    print()
    print("=== Training LSTM LM (3 epochs) ===")
    t2 = time.time()
    lm_result = trainer.train_lm(epochs=3, lr=0.003, verbose=True)
    print(f"Epochs: {lm_result['epochs_trained']}")
    print(f"Time: {time.time()-t2:.1f}s")
    for e in lm_result["training_log"][-5:]:
        print(f"  Epoch {e['epoch']}: loss={e['avg_loss']:.4f} texts={e['n_texts']}")

    # 5. Export LM weights
    print()
    print("=== Exporting LM weights ===")
    lm_path = trainer.export_lm_weights(lm_result, "texthumanize/weights")
    size = os.path.getsize(lm_path)
    print(f"  LM: {lm_path} ({size} bytes)")

    print(f"\nTotal time: {time.time()-t0:.1f}s")


if __name__ == "__main__":
    main()
