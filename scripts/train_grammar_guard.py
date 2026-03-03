"""Training script for Grammar Guard MLP.

Generates synthetic artifact training data by:
1. Taking human-written sentences (from HC3/Ghostbuster)
2. Corrupting them with simulated humanization artifacts:
   - Replace words with uncommon synonyms (bad collocation)
   - Inject formal connectors where not needed
   - Replace adjectives violating agreement (RU/UK)
   - Insert rare words in common contexts
3. Train MLP on (features → artifact/clean) classification

Usage:
    python scripts/train_grammar_guard.py [--samples 5000] [--epochs 100]
"""

from __future__ import annotations

import json
import math
import os
import random
import sys
import time

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from texthumanize.grammar_guard import extract_sentence_features

# ── Training data generation ──────────────────────────────────

# Common words and their rare synonyms that create artifacts when swapped
_ARTIFACT_SWAPS_EN = {
    'use': ['utilize', 'employ', 'leverage', 'harness'],
    'help': ['facilitate', 'expedite', 'ameliorate'],
    'show': ['demonstrate', 'elucidate', 'illuminate'],
    'get': ['procure', 'acquire', 'obtain', 'garner'],
    'make': ['fabricate', 'construct', 'engender'],
    'big': ['substantial', 'considerable', 'monumental'],
    'good': ['salubrious', 'exemplary', 'meritorious'],
    'bad': ['deleterious', 'detrimental', 'nefarious'],
    'important': ['paramount', 'quintessential', 'indispensable'],
    'try': ['endeavor', 'strive', 'undertake'],
    'start': ['commence', 'inaugurate', 'initiate'],
    'end': ['terminate', 'culminate', 'conclude'],
    'give': ['bestow', 'confer', 'impart'],
    'think': ['contemplate', 'cogitate', 'ponder'],
    'need': ['necessitate', 'require', 'mandate'],
}

_ARTIFACT_SWAPS_RU = {
    'использовать': ['утилизировать', 'применять', 'задействовать'],
    'помочь': ['содействовать', 'способствовать', 'фасилитировать'],
    'показать': ['продемонстрировать', 'проиллюстрировать'],
    'получить': ['приобрести', 'заполучить', 'снискать'],
    'сделать': ['реализовать', 'имплементировать', 'осуществить'],
    'большой': ['масштабный', 'грандиозный', 'монументальный'],
    'хороший': ['превосходный', 'безупречный', 'образцовый'],
    'плохой': ['пагубный', 'деструктивный', 'порочный'],
    'важный': ['первостепенный', 'кардинальный', 'эссенциальный'],
    'начать': ['инициировать', 'запустить', 'учредить'],
}

_FORCED_CONNECTORS_EN = [
    'Furthermore, ', 'Moreover, ', 'Additionally, ',
    'Consequently, ', 'Nevertheless, ', 'Accordingly, ',
    'Notwithstanding, ', 'Henceforth, ',
]

_FORCED_CONNECTORS_RU = [
    'Кроме того, ', 'Более того, ', 'Следовательно, ',
    'Тем не менее, ', 'Соответственно, ', 'Таким образом, ',
    'Вместе с тем, ', 'В связи с этим, ',
]


def _load_human_sentences(lang: str = "en", max_samples: int = 3000) -> list[str]:
    """Load human-written sentences from cached training data."""
    data_dir = os.path.join(
        os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
        'data',
    )

    sentences: list[str] = []
    import re

    # Load from JSONL files (hc3, ghostbuster, user)
    for fname in sorted(os.listdir(data_dir)) if os.path.isdir(data_dir) else []:
        if not fname.endswith('.jsonl'):
            continue
        fpath = os.path.join(data_dir, fname)
        try:
            with open(fpath, 'r', encoding='utf-8') as f:
                for line in f:
                    try:
                        obj = json.loads(line)
                        # Only take human text (label=0)
                        if obj.get('label', 1.0) > 0.5:
                            continue
                        text = obj.get('text', '')
                        if not text or len(text) < 40:
                            continue
                        # Split into sentences
                        sents = re.split(r'(?<=[.!?])\s+(?=[A-Z])', text)
                        for s in sents:
                            s = s.strip()
                            if 20 < len(s) < 400 and len(s.split()) >= 5:
                                sentences.append(s)
                    except json.JSONDecodeError:
                        continue
                    if len(sentences) >= max_samples * 2:
                        break
        except Exception:
            continue
        if len(sentences) >= max_samples * 2:
            break

    # Deduplicate and shuffle
    rng = random.Random(42)
    sentences = list(set(sentences))
    rng.shuffle(sentences)

    if len(sentences) < 100:
        print(f"⚠ Only {len(sentences)} real sentences found. Generating synthetic data…")
        sentences.extend(_generate_synthetic_sentences(lang, max_samples - len(sentences)))

    return sentences[:max_samples]


def _generate_synthetic_sentences(lang: str, count: int) -> list[str]:
    """Generate simple synthetic clean sentences for training."""
    rng = random.Random(42)

    templates_en = [
        "The {adj} {noun} {verb} the {adj2} {noun2} in the {place}.",
        "We {verb} a {adj} {noun} for our {noun2}.",
        "This {noun} is very {adj} and {adj2}.",
        "{Name} went to the {place} to {verb} a {noun}.",
        "The team {past} the {adj} {noun} last {time}.",
    ]
    adj_en = ['new', 'old', 'great', 'small', 'simple', 'complex', 'quick',
              'slow', 'bright', 'dark', 'long', 'short', 'clean', 'fresh']
    noun_en = ['system', 'project', 'method', 'tool', 'plan', 'team',
               'idea', 'result', 'process', 'model', 'task', 'issue']
    verb_en = ['created', 'built', 'tested', 'found', 'used', 'fixed',
               'checked', 'started', 'finished', 'improved', 'changed']
    place_en = ['office', 'lab', 'school', 'park', 'city', 'library']
    name_en = ['Alice', 'Bob', 'Carol', 'Dave', 'Eve']

    templates_ru = [
        "{Adj} {noun} {verb} в {place}.",
        "Мы {verb} {adj} {noun} для {noun2}.",
        "Этот {noun} очень {adj} и {adj2}.",
        "{Name} пошёл в {place} чтобы {verb} {noun}.",
    ]
    adj_ru = ['новый', 'старый', 'большой', 'маленький', 'простой',
              'быстрый', 'чистый', 'яркий', 'тихий', 'длинный']
    noun_ru = ['проект', 'метод', 'план', 'результат', 'задача',
               'система', 'модель', 'процесс', 'вопрос', 'решение']
    verb_ru = ['создал', 'построил', 'проверил', 'нашёл', 'использовал',
               'исправил', 'начал', 'закончил', 'улучшил']
    place_ru = ['офис', 'лабораторию', 'школу', 'парк', 'город']
    name_ru = ['Алексей', 'Мария', 'Иван', 'Ольга', 'Дмитрий']

    sentences = []
    for _ in range(count):
        if lang == 'ru':
            tmpl = rng.choice(templates_ru)
            s = tmpl.format(
                Adj=rng.choice(adj_ru).capitalize(),
                adj=rng.choice(adj_ru), adj2=rng.choice(adj_ru),
                noun=rng.choice(noun_ru), noun2=rng.choice(noun_ru),
                verb=rng.choice(verb_ru),
                place=rng.choice(place_ru),
                Name=rng.choice(name_ru),
            )
        else:
            tmpl = rng.choice(templates_en)
            s = tmpl.format(
                adj=rng.choice(adj_en), adj2=rng.choice(adj_en),
                noun=rng.choice(noun_en), noun2=rng.choice(noun_en),
                verb=rng.choice(verb_en), past=rng.choice(verb_en),
                place=rng.choice(place_en),
                Name=rng.choice(name_en), time=rng.choice(['week', 'month', 'year']),
            )
        sentences.append(s)

    return sentences


def _corrupt_sentence(sentence: str, lang: str, rng: random.Random) -> str:
    """Create an artifact version of a clean sentence.

    Apply multiple corruption types to create clearly distinguishable artifacts.
    """
    import re
    swaps = _ARTIFACT_SWAPS_RU if lang == 'ru' else _ARTIFACT_SWAPS_EN
    connectors = _FORCED_CONNECTORS_RU if lang == 'ru' else _FORCED_CONNECTORS_EN

    result = sentence
    # Apply 1-3 corruptions per sentence
    n_corruptions = rng.randint(1, 3)
    corruption_types = rng.sample(
        ['swap', 'connector', 'double_swap', 'repeat_word',
         'formalize', 'wrong_collocation'],
        min(n_corruptions, 6),
    )

    for corruption_type in corruption_types:
        if corruption_type in ('swap', 'double_swap'):
            lower = result.lower()
            applied = 0
            max_swaps = 2 if corruption_type == 'double_swap' else 1
            for word, replacements in swaps.items():
                if word in lower and applied < max_swaps:
                    repl = rng.choice(replacements)
                    pattern = re.compile(re.escape(word), re.IGNORECASE)
                    match = pattern.search(result)
                    if match:
                        found = match.group()
                        if found[0].isupper():
                            repl = repl[0].upper() + repl[1:]
                        result = result[:match.start()] + repl + result[match.end():]
                        applied += 1

        elif corruption_type == 'connector':
            conn = rng.choice(connectors)
            if result[0].isupper():
                result = conn + result[0].lower() + result[1:]
            else:
                result = conn + result

        elif corruption_type == 'repeat_word':
            # Insert a repeated content word
            words = result.split()
            if len(words) > 5:
                content = [w for w in words if len(w) > 4]
                if content:
                    repeated = rng.choice(content)
                    pos = rng.randint(2, len(words) - 1)
                    words.insert(pos, repeated.lower())
                    result = ' '.join(words)

        elif corruption_type == 'formalize':
            # Replace casual constructions with formal ones
            formalizations = {
                "don't": "do not", "can't": "cannot", "won't": "will not",
                "it's": "it is", "that's": "that is", "there's": "there is",
                "I'm": "I am", "we're": "we are", "they're": "they are",
                "I've": "I have", "we've": "we have",
            }
            for casual, formal in formalizations.items():
                if casual in result:
                    result = result.replace(casual, formal, 1)
                    break

        elif corruption_type == 'wrong_collocation':
            # Replace a common word with a semantically close but collocatively wrong one
            wrong_collocs = {
                'make': 'do', 'do': 'make', 'take': 'bring', 'bring': 'take',
                'say': 'tell', 'tell': 'say', 'speak': 'talk', 'talk': 'speak',
                'big': 'large', 'large': 'big',
            }
            words = result.split()
            for i, w in enumerate(words):
                wl = w.lower().rstrip('.,;:!?')
                if wl in wrong_collocs and rng.random() < 0.5:
                    replacement = wrong_collocs[wl]
                    # Preserve case
                    if w[0].isupper():
                        replacement = replacement.capitalize()
                    # Preserve trailing punctuation
                    trail = w[len(wl):]
                    words[i] = replacement + trail
                    break
            result = ' '.join(words)

    return result


def _extract_features_batch(
    sentences: list[str],
    lang: str,
) -> list[list[float]]:
    """Extract features for each sentence with context."""
    all_features = []
    for i, sent in enumerate(sentences):
        ctx_before = sentences[i - 1] if i > 0 else ""
        ctx_after = sentences[i + 1] if i < len(sentences) - 1 else ""
        features = extract_sentence_features(sent, ctx_before, ctx_after, lang)
        all_features.append(features)
    return all_features


def _train_mlp(
    X: list[list[float]],
    y: list[float],
    hidden_sizes: tuple[int, ...] = (16, 8),
    lr: float = 0.01,
    epochs: int = 100,
    seed: int = 42,
) -> dict:
    """Train a small MLP with backpropagation.

    Returns weight dict: {W1, B1, W2, B2, W3, B3, means, stds, metrics}
    """
    rng = random.Random(seed)
    n_features = len(X[0])
    n_samples = len(X)

    # Compute normalization stats
    means = [0.0] * n_features
    stds = [0.0] * n_features
    for i in range(n_features):
        vals = [x[i] for x in X]
        means[i] = sum(vals) / len(vals)
        var = sum((v - means[i]) ** 2 for v in vals) / len(vals)
        stds[i] = var ** 0.5

    # Normalize
    X_norm = []
    for x in X:
        xn = []
        for i in range(n_features):
            if stds[i] > 1e-8:
                xn.append(max(-3.0, min(3.0, (x[i] - means[i]) / stds[i])))
            else:
                xn.append(0.0)
        X_norm.append(xn)

    # Initialize weights (Xavier)
    def _init_weights(rows: int, cols: int) -> list[list[float]]:
        scale = (2.0 / (rows + cols)) ** 0.5
        return [[rng.gauss(0, scale) for _ in range(cols)] for _ in range(rows)]

    def _init_bias(size: int) -> list[float]:
        return [0.0] * size

    h1_size, h2_size = hidden_sizes
    W1 = _init_weights(h1_size, n_features)
    B1 = _init_bias(h1_size)
    W2 = _init_weights(h2_size, h1_size)
    B2 = _init_bias(h2_size)
    W3 = _init_weights(1, h2_size)
    B3 = _init_bias(1)

    def _relu(x: float) -> float:
        return max(0.0, x)

    def _sigmoid(x: float) -> float:
        if x > 20: return 1.0
        if x < -20: return 0.0
        return 1.0 / (1.0 + math.exp(-x))

    def _forward(x: list[float]) -> tuple[list[float], list[float], float]:
        # Layer 1
        h1 = []
        for j in range(h1_size):
            acc = B1[j]
            for i in range(n_features):
                acc += W1[j][i] * x[i]
            h1.append(_relu(acc))
        # Layer 2
        h2 = []
        for j in range(h2_size):
            acc = B2[j]
            for i in range(h1_size):
                acc += W2[j][i] * h1[i]
            h2.append(_relu(acc))
        # Output
        logit = B3[0]
        for i in range(h2_size):
            logit += W3[0][i] * h2[i]
        return h1, h2, _sigmoid(logit)

    # Training loop (mini-batch SGD)
    batch_size = 32
    best_loss = float('inf')
    best_weights = None

    print(f"Training Grammar Guard MLP: {n_features}→{h1_size}→{h2_size}→1")
    print(f"Samples: {n_samples}, Epochs: {epochs}, LR: {lr}")

    for epoch in range(epochs):
        # Shuffle
        indices = list(range(n_samples))
        rng.shuffle(indices)

        total_loss = 0.0
        correct = 0

        for batch_start in range(0, n_samples, batch_size):
            batch_idx = indices[batch_start:batch_start + batch_size]

            # Accumulate gradients
            gW1 = [[0.0] * n_features for _ in range(h1_size)]
            gB1 = [0.0] * h1_size
            gW2 = [[0.0] * h1_size for _ in range(h2_size)]
            gB2 = [0.0] * h2_size
            gW3 = [[0.0] * h2_size]
            gB3 = [0.0]

            for idx in batch_idx:
                x = X_norm[idx]
                target = y[idx]

                h1, h2, pred = _forward(x)

                # BCE loss gradient
                eps = 1e-7
                pred_clip = max(eps, min(1 - eps, pred))
                loss = -(target * math.log(pred_clip) + (1 - target) * math.log(1 - pred_clip))
                total_loss += loss

                if (pred >= 0.5) == (target >= 0.5):
                    correct += 1

                # Backprop
                dout = pred_clip - target  # d(BCE)/d(logit) = pred - target

                # Layer 3 gradients
                for i in range(h2_size):
                    gW3[0][i] += dout * h2[i]
                gB3[0] += dout

                # Layer 2 gradients
                dh2 = [0.0] * h2_size
                for i in range(h2_size):
                    dh2[i] = dout * W3[0][i] * (1.0 if h2[i] > 0 else 0.0)  # ReLU grad
                    for j in range(h1_size):
                        gW2[i][j] += dh2[i] * h1[j]
                    gB2[i] += dh2[i]

                # Layer 1 gradients
                dh1 = [0.0] * h1_size
                for i in range(h1_size):
                    for j in range(h2_size):
                        dh1[i] += dh2[j] * W2[j][i]
                    dh1[i] *= (1.0 if h1[i] > 0 else 0.0)  # ReLU grad
                    for j in range(n_features):
                        gW1[i][j] += dh1[i] * x[j]
                    gB1[i] += dh1[i]

            # Update weights
            bs = len(batch_idx)
            for j in range(h1_size):
                for i in range(n_features):
                    W1[j][i] -= lr * gW1[j][i] / bs
                B1[j] -= lr * gB1[j] / bs
            for j in range(h2_size):
                for i in range(h1_size):
                    W2[j][i] -= lr * gW2[j][i] / bs
                B2[j] -= lr * gB2[j] / bs
            for i in range(h2_size):
                W3[0][i] -= lr * gW3[0][i] / bs
            B3[0] -= lr * gB3[0] / bs

        avg_loss = total_loss / n_samples
        accuracy = correct / n_samples

        if avg_loss < best_loss:
            best_loss = avg_loss
            best_weights = {
                'W1': [row[:] for row in W1],
                'B1': B1[:],
                'W2': [row[:] for row in W2],
                'B2': B2[:],
                'W3': [row[:] for row in W3],
                'B3': B3[:],
            }

        if (epoch + 1) % 10 == 0 or epoch == 0:
            print(f"  Epoch {epoch + 1:3d}: loss={avg_loss:.4f}, acc={accuracy:.1%}")

    print(f"\nBest loss: {best_loss:.4f}")

    return {
        **best_weights,  # type: ignore[dict-item]
        'means': means,
        'stds': stds,
        'metrics': {
            'best_loss': best_loss,
            'final_accuracy': correct / n_samples,
            'n_features': n_features,
            'architecture': f"{n_features}→{h1_size}→{h2_size}→1",
        },
    }


def main():
    import argparse

    parser = argparse.ArgumentParser(description="Train Grammar Guard MLP")
    parser.add_argument('--samples', type=int, default=3000, help='Number of samples per class')
    parser.add_argument('--epochs', type=int, default=80, help='Training epochs')
    parser.add_argument('--lr', type=float, default=0.008, help='Learning rate')
    parser.add_argument('--lang', type=str, default='en', help='Language for training data')
    args = parser.parse_args()

    print("=" * 60)
    print("Grammar Guard MLP Training")
    print("=" * 60)

    # 1. Load clean sentences
    print(f"\n1. Loading human sentences (lang={args.lang})…")
    clean_sentences = _load_human_sentences(args.lang, args.samples)
    print(f"   Loaded {len(clean_sentences)} clean sentences")

    # 2. Generate artifact sentences
    print("\n2. Generating artifact sentences…")
    rng = random.Random(42)
    artifact_sentences = [
        _corrupt_sentence(s, args.lang, rng)
        for s in clean_sentences
    ]
    print(f"   Generated {len(artifact_sentences)} artifact sentences")

    # 3. Extract features
    print("\n3. Extracting features…")
    t0 = time.time()
    clean_features = _extract_features_batch(clean_sentences, args.lang)
    artifact_features = _extract_features_batch(artifact_sentences, args.lang)
    t_feat = time.time() - t0
    print(f"   Extracted {len(clean_features) + len(artifact_features)} feature vectors in {t_feat:.1f}s")

    # 4. Combine dataset
    X = clean_features + artifact_features
    y = [0.0] * len(clean_features) + [1.0] * len(artifact_features)

    # Shuffle together
    combined = list(zip(X, y))
    rng.shuffle(combined)
    X = [c[0] for c in combined]
    y = [c[1] for c in combined]

    # 5. Train
    print(f"\n4. Training ({args.epochs} epochs)…")
    weights = _train_mlp(X, y, hidden_sizes=(16, 8), lr=args.lr, epochs=args.epochs)

    # 6. Save weights
    out_dir = os.path.join(
        os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
        'texthumanize', 'weights',
    )
    os.makedirs(out_dir, exist_ok=True)
    out_path = os.path.join(out_dir, 'grammar_guard_weights.json')

    with open(out_path, 'w') as f:
        json.dump(weights, f, indent=2)
    print(f"\n✅ Weights saved to {out_path}")
    print(f"   Architecture: {weights['metrics']['architecture']}")
    print(f"   Final accuracy: {weights['metrics']['final_accuracy']:.1%}")
    print(f"   Best loss: {weights['metrics']['best_loss']:.4f}")

    # 7. Quick eval
    print("\n5. Quick evaluation…")
    tp = fp = tn = fn = 0
    n_eval = min(200, len(X))
    for i in range(n_eval):
        features = X[i]
        label = y[i]

        # Normalize using training stats
        normed = []
        for j, (v, m, s) in enumerate(zip(features, weights['means'], weights['stds'])):
            if s > 1e-8:
                normed.append(max(-3.0, min(3.0, (v - m) / s)))
            else:
                normed.append(0.0)

        # Forward pass with best weights
        W1 = weights['W1']
        B1 = weights['B1']
        W2 = weights['W2']
        B2 = weights['B2']
        W3 = weights['W3']
        B3 = weights['B3']

        h1 = [max(0.0, B1[k] + sum(W1[k][j] * normed[j] for j in range(12)))
               for k in range(16)]
        h2 = [max(0.0, B2[k] + sum(W2[k][j] * h1[j] for j in range(16)))
               for k in range(8)]
        logit = B3[0] + sum(W3[0][j] * h2[j] for j in range(8))
        pred = 1.0 / (1.0 + math.exp(-max(-20, min(20, logit))))

        if pred >= 0.5 and label >= 0.5:
            tp += 1
        elif pred >= 0.5 and label < 0.5:
            fp += 1
        elif pred < 0.5 and label < 0.5:
            tn += 1
        else:
            fn += 1

    prec = tp / max(tp + fp, 1)
    rec = tp / max(tp + fn, 1)
    f1 = 2 * prec * rec / max(prec + rec, 1e-8)
    acc = (tp + tn) / n_eval

    print(f"   Accuracy:  {acc:.1%}")
    print(f"   Precision: {prec:.1%}")
    print(f"   Recall:    {rec:.1%}")
    print(f"   F1:        {f1:.1%}")


if __name__ == '__main__':
    main()
