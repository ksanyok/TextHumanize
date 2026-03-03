#!/usr/bin/env python3
"""Тренировка MLP-детектора на реальных данных (HC3 + Ghostbuster + GPT).

Этапы:
1. Извлечение фич из текстов (с кэшированием на диск)
2. Балансировка классов
3. Обучение MLP [35, 256, 128, 64, 1]
4. Экспорт весов в формат, совместимый с NeuralAIDetector
"""
import json
import logging
import math
import os
import random
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import numpy as np

from texthumanize.data_loader import TextSample, load_auto, dataset_stats
from texthumanize.neural_detector import extract_features, normalize_features

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[logging.StreamHandler()],
)
log = logging.getLogger("train_v2")

# ── Пути ──────────────────────────────────────────────────────────────────
DATA_DIR = Path("data")
CACHE_DIR = DATA_DIR / "feature_cache"
WEIGHTS_DIR = Path("texthumanize") / "weights"

# ── Параметры ─────────────────────────────────────────────────────────────
MAX_SAMPLES = 20_000        # макс. семплов для обучения (для скорости)
ARCH = [35, 256, 128, 64, 1]
EPOCHS = 80
LR = 0.001
WEIGHT_DECAY = 0.01
PATIENCE = 15
BATCH_PRINT = 500           # каждые N семплов логировать прогресс
SEED = 42


# ══════════════════════════════════════════════════════════════════════════
# 1. Кэшированное извлечение фич
# ══════════════════════════════════════════════════════════════════════════

def _cache_path(name: str) -> Path:
    CACHE_DIR.mkdir(parents=True, exist_ok=True)
    return CACHE_DIR / f"{name}.npz"


def extract_with_cache(
    samples: list[TextSample],
    cache_name: str,
) -> tuple[np.ndarray, np.ndarray]:
    """Извлечь фичи из текстов с кэшированием на диск."""
    cp = _cache_path(cache_name)
    if cp.exists():
        log.info("Загружаю кэш фич: %s", cp)
        d = np.load(cp)
        return d["X"], d["y"]

    log.info("Извлекаю фичи из %d семплов (может занять 10-30 мин)...", len(samples))
    X_list = []
    y_list = []
    errors = 0
    t0 = time.time()

    for i, s in enumerate(samples):
        if (i + 1) % BATCH_PRINT == 0:
            elapsed = time.time() - t0
            speed = (i + 1) / elapsed
            eta = (len(samples) - i - 1) / max(speed, 0.1)
            log.info(
                "  [%d/%d] %.0f сэмпл/с, ETA %.0f сек, ошибок=%d",
                i + 1, len(samples), speed, eta, errors,
            )
        try:
            raw = extract_features(s.text, s.lang)
            norm = normalize_features(raw, lang=s.lang)
            X_list.append(norm)
            y_list.append(s.label)
        except Exception:
            errors += 1

    X = np.array(X_list, dtype=np.float32)
    y = np.array(y_list, dtype=np.float32)

    log.info(
        "Извлечено: %d/%d (ошибок=%d) за %.0f сек",
        len(X_list), len(samples), errors, time.time() - t0,
    )

    np.savez_compressed(cp, X=X, y=y)
    log.info("Кэш сохранён: %s (%.1f MB)", cp, cp.stat().st_size / 1e6)
    return X, y


# ══════════════════════════════════════════════════════════════════════════
# 2. MLP на numpy (оптимизированный для батч-обучения)
# ══════════════════════════════════════════════════════════════════════════

def _sigmoid(x: np.ndarray) -> np.ndarray:
    return np.where(x >= 0, 1 / (1 + np.exp(-x)), np.exp(x) / (1 + np.exp(x)))


def _relu(x: np.ndarray) -> np.ndarray:
    return np.maximum(0, x)


def _relu_grad(x: np.ndarray) -> np.ndarray:
    return (x > 0).astype(np.float32)


class BatchMLP:
    """MLP с батч-операциями на numpy — в 100x быстрее поэлементного."""

    def __init__(self, sizes: list[int], seed: int = 42):
        self.sizes = sizes
        rng = np.random.RandomState(seed)
        self.W: list[np.ndarray] = []
        self.b: list[np.ndarray] = []
        for i in range(len(sizes) - 1):
            fan_in, fan_out = sizes[i], sizes[i + 1]
            # He initialization
            std = math.sqrt(2.0 / fan_in)
            self.W.append(rng.randn(fan_in, fan_out).astype(np.float32) * std)
            self.b.append(np.zeros(fan_out, dtype=np.float32))

    @property
    def param_count(self) -> int:
        return sum(w.size + b.size for w, b in zip(self.W, self.b))

    def forward(self, X: np.ndarray) -> tuple[np.ndarray, list[np.ndarray]]:
        """Forward pass: X shape (batch, 35) → probs shape (batch,)."""
        caches = [X]
        h = X
        for i, (w, b) in enumerate(zip(self.W, self.b)):
            z = h @ w + b
            if i < len(self.W) - 1:
                h = _relu(z)
            else:
                h = z  # последний слой — без активации (logit)
            caches.append(h)
        probs = _sigmoid(h.squeeze(-1))
        return probs, caches

    def backward(
        self,
        probs: np.ndarray,
        y: np.ndarray,
        caches: list[np.ndarray],
        clip: float = 5.0,
    ) -> list[tuple[np.ndarray, np.ndarray]]:
        """Backward pass: возвращает [(dW, db), ...] для каждого слоя."""
        batch = probs.shape[0]
        # dL/d(logit) = probs - y
        dz = (probs - y).reshape(batch, 1)

        grads: list[tuple[np.ndarray, np.ndarray]] = []
        for i in range(len(self.W) - 1, -1, -1):
            h = caches[i]       # вход в слой i
            dW = (h.T @ dz) / batch
            db = dz.mean(axis=0).squeeze()
            # Clip
            np.clip(dW, -clip, clip, out=dW)
            np.clip(db, -clip, clip, out=db)
            grads.append((dW, db))
            if i > 0:
                dz = (dz @ self.W[i].T) * _relu_grad(caches[i])
        grads.reverse()
        return grads

    def predict(self, X: np.ndarray) -> np.ndarray:
        probs, _ = self.forward(X)
        return probs

    def to_dict(self) -> dict:
        return {
            "sizes": self.sizes,
            "weights": [w.tolist() for w in self.W],
            "biases": [b.tolist() for b in self.b],
        }

    @classmethod
    def from_dict(cls, d: dict) -> "BatchMLP":
        mlp = cls(d["sizes"])
        for i, (w, b) in enumerate(zip(d["weights"], d["biases"])):
            mlp.W[i] = np.array(w, dtype=np.float32)
            mlp.b[i] = np.array(b, dtype=np.float32)
        return mlp


# ══════════════════════════════════════════════════════════════════════════
# 3. AdamW
# ══════════════════════════════════════════════════════════════════════════

class BatchAdamW:
    def __init__(self, lr=0.001, beta1=0.9, beta2=0.999, eps=1e-8, wd=0.01):
        self.lr = lr
        self.beta1 = beta1
        self.beta2 = beta2
        self.eps = eps
        self.wd = wd
        self.t = 0
        self._m: dict[int, np.ndarray] = {}
        self._v: dict[int, np.ndarray] = {}

    def step(self, param_id: int, param: np.ndarray, grad: np.ndarray) -> np.ndarray:
        if param_id not in self._m:
            self._m[param_id] = np.zeros_like(param)
            self._v[param_id] = np.zeros_like(param)
        self.t += 1
        self._m[param_id] = self.beta1 * self._m[param_id] + (1 - self.beta1) * grad
        self._v[param_id] = self.beta2 * self._v[param_id] + (1 - self.beta2) * grad ** 2
        m_hat = self._m[param_id] / (1 - self.beta1 ** self.t)
        v_hat = self._v[param_id] / (1 - self.beta2 ** self.t)
        param = param - self.lr * (m_hat / (np.sqrt(v_hat) + self.eps) + self.wd * param)
        return param


# ══════════════════════════════════════════════════════════════════════════
# 4. Обучение
# ══════════════════════════════════════════════════════════════════════════

def bce_loss(probs: np.ndarray, y: np.ndarray) -> float:
    eps = 1e-7
    p = np.clip(probs, eps, 1 - eps)
    return float(-(y * np.log(p) + (1 - y) * np.log(1 - p)).mean())


def eval_metrics(mlp: BatchMLP, X: np.ndarray, y: np.ndarray, thr: float = 0.5) -> dict:
    probs = mlp.predict(X)
    preds = (probs >= thr).astype(int)
    actual = (y >= 0.5).astype(int)
    tp = int(((preds == 1) & (actual == 1)).sum())
    fp = int(((preds == 1) & (actual == 0)).sum())
    tn = int(((preds == 0) & (actual == 0)).sum())
    fn = int(((preds == 0) & (actual == 1)).sum())
    n = len(y)
    prec = tp / max(tp + fp, 1)
    rec = tp / max(tp + fn, 1)
    f1 = 2 * prec * rec / max(prec + rec, 1e-9)
    return {
        "acc": round((tp + tn) / n, 4),
        "prec": round(prec, 4),
        "rec": round(rec, 4),
        "f1": round(f1, 4),
        "loss": round(bce_loss(probs, y), 4),
    }


def train(
    X_train: np.ndarray,
    y_train: np.ndarray,
    X_val: np.ndarray,
    y_val: np.ndarray,
    arch: list[int] = None,
    epochs: int = EPOCHS,
    lr: float = LR,
    batch_size: int = 256,
    patience: int = PATIENCE,
) -> tuple[BatchMLP, dict]:
    if arch is None:
        arch = ARCH

    mlp = BatchMLP(arch, seed=SEED)
    opt = BatchAdamW(lr=lr, wd=WEIGHT_DECAY)
    log.info("Архитектура: %s (%d параметров)", arch, mlp.param_count)
    log.info("Тренировка: %d семплов, валидация: %d семплов", len(X_train), len(X_val))

    best_f1 = 0.0
    best_dict = None
    wait = 0
    t0 = time.time()

    for epoch in range(epochs):
        # Shuffle
        idx = np.random.RandomState(SEED + epoch).permutation(len(X_train))
        X_shuf = X_train[idx]
        y_shuf = y_train[idx]

        epoch_loss = 0.0
        n_batches = 0
        for start in range(0, len(X_train), batch_size):
            Xb = X_shuf[start : start + batch_size]
            yb = y_shuf[start : start + batch_size]
            probs, caches = mlp.forward(Xb)
            epoch_loss += bce_loss(probs, yb)
            n_batches += 1
            grads = mlp.backward(probs, yb, caches)
            for i, (dW, db) in enumerate(grads):
                pid_w = i * 2
                pid_b = i * 2 + 1
                mlp.W[i] = opt.step(pid_w, mlp.W[i], dW)
                mlp.b[i] = opt.step(pid_b, mlp.b[i], db)

        avg_loss = epoch_loss / max(n_batches, 1)
        vm = eval_metrics(mlp, X_val, y_val)

        if (epoch + 1) % 5 == 0 or epoch == 0:
            elapsed = time.time() - t0
            log.info(
                "Эпоха %3d/%d — loss=%.4f | val: acc=%.4f f1=%.4f prec=%.4f rec=%.4f (%.0fs)",
                epoch + 1, epochs, avg_loss,
                vm["acc"], vm["f1"], vm["prec"], vm["rec"], elapsed,
            )

        if vm["f1"] > best_f1:
            best_f1 = vm["f1"]
            best_dict = mlp.to_dict()
            wait = 0
        else:
            wait += 1
            if wait >= patience:
                log.info("Early stopping: эпоха %d, лучший F1=%.4f", epoch + 1, best_f1)
                break

    if best_dict:
        mlp = BatchMLP.from_dict(best_dict)

    total_time = time.time() - t0
    log.info("Обучение завершено за %.0f сек. Лучший val F1=%.4f", total_time, best_f1)
    return mlp, {"best_val_f1": best_f1, "epochs": epoch + 1, "time": total_time}


# ══════════════════════════════════════════════════════════════════════════
# 5. Экспорт весов
# ══════════════════════════════════════════════════════════════════════════

def export_legacy(mlp: BatchMLP, output_dir: str = str(WEIGHTS_DIR)) -> str:
    """Экспорт в формат, совместимый с FeedForwardNet / NeuralAIDetector."""
    os.makedirs(output_dir, exist_ok=True)

    # Конвертируем в формат FeedForwardNet (DenseLayer ожидает weights[out][in])
    layers = []
    for i, (w, b) in enumerate(zip(mlp.W, mlp.b)):
        act = "relu" if i < len(mlp.W) - 1 else "linear"
        layers.append({
            "weights": w.T.tolist(),  # транспонируем: (in,out) → (out,in)
            "bias": b.tolist(),       # ед.число — как ожидает FeedForwardNet
            "activation": act,
            "input_size": w.shape[0],
            "output_size": w.shape[1],
        })

    config = {
        "version": 2,
        "architecture": mlp.sizes,
        "layers": layers,
        "trained": True,
        "training_info": {
            "method": "training_v2_batch",
            "samples": "hc3+ghostbuster+gpt",
        },
    }

    # Несжатый JSON (для совместимости)
    v2_path = os.path.join(output_dir, "detector_v2.json")
    with open(v2_path, "w") as f:
        json.dump(config, f)
    log.info("Сохранено: %s (%.1f KB)", v2_path, os.path.getsize(v2_path) / 1024)

    # Сжатый формат legacy
    try:
        from texthumanize.neural_engine import compress_weights
        blob = compress_weights(config)
        legacy_path = os.path.join(output_dir, "detector_weights.json.zb85")
        with open(legacy_path, "w") as f:
            f.write(blob)
        log.info("Legacy формат: %s (%.1f KB)", legacy_path, os.path.getsize(legacy_path) / 1024)
        return legacy_path
    except Exception as e:
        log.warning("Не удалось экспортировать legacy формат: %s", e)
        return v2_path


# ══════════════════════════════════════════════════════════════════════════
# 6. main
# ══════════════════════════════════════════════════════════════════════════

def main():
    print("=" * 60)
    print("  ОБУЧЕНИЕ AI-ДЕТЕКТОРА v2")
    print("  Данные: HC3 + Ghostbuster + GPT")
    print("=" * 60)

    # 1. Загрузка данных
    data_files = list(DATA_DIR.glob("*_training.jsonl"))
    if not data_files:
        log.error("Нет файлов в %s! Сначала скачайте данные.", DATA_DIR)
        sys.exit(1)

    log.info("Найдены файлы данных:")
    all_samples = []
    for f in sorted(data_files):
        samples = load_auto(str(f))
        log.info("  %s: %d семплов", f.name, len(samples))
        all_samples.extend(samples)

    log.info("Всего загружено: %d семплов", len(all_samples))
    stats = dataset_stats(all_samples)
    log.info("Статистика: %s", stats)

    # Ограничиваем для скорости
    if len(all_samples) > MAX_SAMPLES:
        rng = random.Random(SEED)
        rng.shuffle(all_samples)
        all_samples = all_samples[:MAX_SAMPLES]
        log.info("Ограничено до %d семплов", MAX_SAMPLES)

    # 2. Извлечение фич (с кэшем)
    X, y = extract_with_cache(all_samples, "all_features")
    log.info("Матрица фич: %s, меток: %s", X.shape, y.shape)
    log.info("Баланс: human=%d (%.1f%%), ai=%d (%.1f%%)",
             (y < 0.5).sum(), (y < 0.5).mean() * 100,
             (y >= 0.5).sum(), (y >= 0.5).mean() * 100)

    # 3. Разделение на train/val/test
    n = len(X)
    idx = np.random.RandomState(SEED).permutation(n)
    n_test = max(int(n * 0.1), 100)
    n_val = max(int(n * 0.1), 100)
    n_train = n - n_test - n_val

    X_train, y_train = X[idx[:n_train]], y[idx[:n_train]]
    X_val, y_val = X[idx[n_train:n_train + n_val]], y[idx[n_train:n_train + n_val]]
    X_test, y_test = X[idx[n_train + n_val:]], y[idx[n_train + n_val:]]

    log.info("Разделение: train=%d, val=%d, test=%d", len(X_train), len(X_val), len(X_test))

    # 4. Обучение
    mlp, results = train(X_train, y_train, X_val, y_val)

    # 5. Тест
    test_metrics = eval_metrics(mlp, X_test, y_test)
    log.info("=" * 50)
    log.info("РЕЗУЛЬТАТЫ НА ТЕСТОВОЙ ВЫБОРКЕ:")
    log.info("  Accuracy:  %.4f", test_metrics["acc"])
    log.info("  Precision: %.4f", test_metrics["prec"])
    log.info("  Recall:    %.4f", test_metrics["rec"])
    log.info("  F1:        %.4f", test_metrics["f1"])
    log.info("  Loss:      %.4f", test_metrics["loss"])
    log.info("=" * 50)

    # 6. Экспорт
    path = export_legacy(mlp)
    log.info("✅ Веса экспортированы: %s", path)
    log.info("Параметров: %d", mlp.param_count)
    log.info("Архитектура: %s", mlp.sizes)

    # Сохраняем результаты
    report = {
        "architecture": mlp.sizes,
        "param_count": mlp.param_count,
        "training": results,
        "test_metrics": test_metrics,
        "data_stats": stats,
    }
    report_path = DATA_DIR / "training_report.json"
    with open(report_path, "w") as f:
        json.dump(report, f, indent=2)
    log.info("Отчёт: %s", report_path)


if __name__ == "__main__":
    main()
