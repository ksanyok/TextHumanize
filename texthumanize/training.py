"""Training infrastructure — backpropagation, Adam optimizer, data generation.

Implements real gradient-based training for the neural detector MLP and
character-level LSTM. All training happens in pure Python — no external
ML libraries required.

Training workflow:
    1. Generate labeled training data (AI vs human text features)
    2. Train MLP detector via backprop + Adam
    3. Train char-LSTM via BPTT + Adam
    4. Export compressed weights to texthumanize/weights/

Usage::

    from texthumanize.training import Trainer
    trainer = Trainer()
    trainer.generate_data(n_samples=5000)
    trainer.train_detector(epochs=50, lr=0.001)
    trainer.train_lm(epochs=20, lr=0.001)
    trainer.export_weights()
"""

from __future__ import annotations

import logging
import math
import os
import random
import re
from typing import Any

from texthumanize.neural_engine import (
    FeedForwardNet,
    LSTMCell,
    Mat,
    Vec,
    _dot,
    _he_init,
    _log_softmax,
    _matvec,
    _sigmoid,
    _softmax,
    _tanh,
    _vecadd,
    _zeros,
    compress_weights,
)

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Binary cross-entropy loss
# ---------------------------------------------------------------------------

def _bce_loss(predicted: float, target: float) -> float:
    """Binary cross-entropy loss."""
    p = max(1e-7, min(1 - 1e-7, predicted))
    return -(target * math.log(p) + (1 - target) * math.log(1 - p))


def _bce_grad(predicted: float, target: float) -> float:
    """Gradient of BCE w.r.t. logit (pre-sigmoid)."""
    return predicted - target


def _cross_entropy_loss(log_probs: Vec, target_idx: int) -> float:
    """Cross-entropy loss for classification."""
    return -log_probs[target_idx]


# ---------------------------------------------------------------------------
# Adam optimizer
# ---------------------------------------------------------------------------

class AdamOptimizer:
    """Adam optimizer for weight updates.

    Implements the Adam algorithm (Kingma & Ba, 2014) with optional
    weight decay (AdamW variant).
    """

    def __init__(
        self,
        lr: float = 0.001,
        beta1: float = 0.9,
        beta2: float = 0.999,
        eps: float = 1e-8,
        weight_decay: float = 0.0,
    ) -> None:
        self.lr = lr
        self.beta1 = beta1
        self.beta2 = beta2
        self.eps = eps
        self.weight_decay = weight_decay
        self._m: dict[str, Any] = {}  # first moments
        self._v: dict[str, Any] = {}  # second moments
        self._t = 0

    def step_vec(self, param_name: str, param: Vec, grad: Vec) -> Vec:
        """Update a vector parameter."""
        self._t += 1
        if param_name not in self._m:
            self._m[param_name] = [0.0] * len(param)
            self._v[param_name] = [0.0] * len(param)

        m = self._m[param_name]
        v = self._v[param_name]
        b1 = self.beta1
        b2 = self.beta2
        eps = self.eps
        wd = self.weight_decay
        lr_t = self.lr * math.sqrt(1 - b2 ** self._t) / (1 - b1 ** self._t)

        for i in range(len(param)):
            g = grad[i]
            if wd > 0:
                g += wd * param[i]
            mi = b1 * m[i] + (1 - b1) * g
            vi = b2 * v[i] + (1 - b2) * g * g
            m[i] = mi
            v[i] = vi
            param[i] -= lr_t * mi / (math.sqrt(vi) + eps)

        return param

    def step_mat(self, param_name: str, param: Mat, grad: Mat) -> Mat:
        """Update a matrix parameter (flattened for efficiency)."""
        n_rows = len(param)
        n_cols = len(param[0]) if n_rows > 0 else 0
        flat_size = n_rows * n_cols

        self._t += 1
        if param_name not in self._m:
            self._m[param_name] = [0.0] * flat_size
            self._v[param_name] = [0.0] * flat_size

        m = self._m[param_name]
        v = self._v[param_name]
        b1 = self.beta1
        b2 = self.beta2
        eps = self.eps
        wd = self.weight_decay
        lr_t = self.lr * math.sqrt(1 - b2 ** self._t) / (1 - b1 ** self._t)

        k = 0
        for i in range(n_rows):
            row_p = param[i]
            row_g = grad[i]
            for j in range(n_cols):
                g = row_g[j]
                if wd > 0:
                    g += wd * row_p[j]
                mi = b1 * m[k] + (1 - b1) * g
                vi = b2 * v[k] + (1 - b2) * g * g
                m[k] = mi
                v[k] = vi
                row_p[j] -= lr_t * mi / (math.sqrt(vi) + eps)
                k += 1

        return param


# ---------------------------------------------------------------------------
# MLP Backpropagation
# ---------------------------------------------------------------------------

class MLPTrainer:
    """Train a FeedForwardNet using backpropagation.

    Supports binary classification (BCE loss) with gradient clipping.
    """

    def __init__(
        self,
        net: FeedForwardNet,
        lr: float = 0.001,
        weight_decay: float = 1e-4,
        clip_grad: float = 5.0,
    ) -> None:
        self.net = net
        self.optimizer = AdamOptimizer(lr=lr, weight_decay=weight_decay)
        self.clip_grad = clip_grad

    def _forward_with_cache(self, x: Vec) -> tuple[float, list[Vec]]:
        """Forward pass caching intermediate activations for backprop."""
        activations = [list(x)]
        current = x
        for layer in self.net.layers:
            pre_act = _vecadd(_matvec(layer.weights, current), layer.bias)
            if layer.activation == "relu":
                current = [max(0.0, v) for v in pre_act]
            elif layer.activation == "sigmoid":
                current = [_sigmoid(v) for v in pre_act]
            elif layer.activation == "tanh":
                current = [_tanh(v) for v in pre_act]
            else:  # linear
                current = list(pre_act)
            activations.append(current)
        # Final sigmoid for binary classification
        logit = current[0]
        prob = _sigmoid(logit)
        return prob, activations

    def _backward(
        self, target: float, prob: float, activations: list[Vec],
    ) -> list[tuple[Mat, Vec]]:
        """Backward pass — compute gradients for all layers."""
        layers = self.net.layers
        n_layers = len(layers)
        grads: list[tuple[Mat, Vec]] = []

        # Gradient of loss w.r.t. output logit
        d_out = [prob - target]  # BCE gradient

        for layer_idx in range(n_layers - 1, -1, -1):
            layer = layers[layer_idx]
            a_in = activations[layer_idx]
            a_out = activations[layer_idx + 1]

            # Gradient through activation
            if layer_idx == n_layers - 1:
                delta = d_out
            else:
                # d_out is delta from next layer
                if layer.activation == "relu":
                    delta = [d * (1.0 if a > 0 else 0.0) for d, a in zip(d_out, a_out)]
                elif layer.activation == "sigmoid":
                    delta = [d * a * (1 - a) for d, a in zip(d_out, a_out)]
                elif layer.activation == "tanh":
                    delta = [d * (1 - a * a) for d, a in zip(d_out, a_out)]
                else:
                    delta = list(d_out)

            # Weight gradient: delta (outer) a_in^T
            dw: Mat = [[delta[i] * a_in[j] for j in range(len(a_in))] for i in range(len(delta))]
            db: Vec = list(delta)

            # Clip gradients
            for i in range(len(dw)):
                for j in range(len(dw[i])):
                    dw[i][j] = max(-self.clip_grad, min(self.clip_grad, dw[i][j]))
            for i in range(len(db)):
                db[i] = max(-self.clip_grad, min(self.clip_grad, db[i]))

            grads.insert(0, (dw, db))

            # Propagate gradient to previous layer
            if layer_idx > 0:
                d_out = [
                    sum(layer.weights[k][j] * delta[k] for k in range(len(delta)))
                    for j in range(len(a_in))
                ]

        return grads

    def train_step(self, x: Vec, target: float) -> float:
        """Single training step. Returns loss."""
        prob, activations = self._forward_with_cache(x)
        loss = _bce_loss(prob, target)

        grads = self._backward(target, prob, activations)

        # Update weights
        for i, (dw, db) in enumerate(grads):
            layer = self.net.layers[i]
            layer.weights = self.optimizer.step_mat(f"layer{i}_w", layer.weights, dw)
            layer.bias = self.optimizer.step_vec(f"layer{i}_b", layer.bias, db)

        return loss

    def train_epoch(
        self,
        data: list[tuple[Vec, float]],
        shuffle: bool = True,
        seed: int = 0,
    ) -> float:
        """Train one epoch over data. Returns mean loss."""
        if shuffle:
            rng = random.Random(seed)
            data = list(data)
            rng.shuffle(data)

        total_loss = 0.0
        for x, y in data:
            total_loss += self.train_step(x, y)
        return total_loss / max(len(data), 1)

    def evaluate(self, data: list[tuple[Vec, float]], threshold: float = 0.5) -> dict[str, float]:
        """Evaluate accuracy, precision, recall, F1 on data."""
        tp = fp = tn = fn = 0
        total_loss = 0.0

        for x, y in data:
            prob = self.net.predict_proba(x)
            total_loss += _bce_loss(prob, y)
            pred = 1 if prob >= threshold else 0
            actual = 1 if y >= 0.5 else 0
            if pred == 1 and actual == 1:
                tp += 1
            elif pred == 1 and actual == 0:
                fp += 1
            elif pred == 0 and actual == 0:
                tn += 1
            else:
                fn += 1

        n = max(len(data), 1)
        precision = tp / max(tp + fp, 1)
        recall = tp / max(tp + fn, 1)
        f1 = 2 * precision * recall / max(precision + recall, 1e-9)

        return {
            "accuracy": (tp + tn) / n,
            "precision": precision,
            "recall": recall,
            "f1": f1,
            "loss": total_loss / n,
            "tp": tp, "fp": fp, "tn": tn, "fn": fn,
        }


# ---------------------------------------------------------------------------
# Training data generation — self-supervised from corpus patterns
# ---------------------------------------------------------------------------

# Representative text samples for feature extraction
_AI_TEXT_TEMPLATES: list[str] = [
    "Furthermore, it is important to note that the utilization of advanced methodologies has significantly contributed to the overall improvement of systemic outcomes. The implementation of comprehensive strategies ensures that all stakeholders benefit from the enhanced framework. Additionally, the integration of holistic approaches facilitates the achievement of optimal results across various domains.",
    "In conclusion, the aforementioned analysis demonstrates that a multifaceted approach is essential for addressing the complexities inherent in modern challenges. By leveraging cutting-edge technologies and fostering collaborative partnerships, organizations can effectively navigate the evolving landscape. Moreover, the systematic evaluation of performance metrics provides valuable insights for continuous improvement.",
    "The comprehensive examination of relevant literature reveals several key findings that merit consideration. Firstly, the data suggests a significant correlation between the implementation of evidence-based practices and positive outcomes. Secondly, the analysis indicates that organizational culture plays a crucial role in determining the success of strategic initiatives.",
    "It is worth noting that the systematic approach to problem-solving has yielded substantial benefits across multiple sectors. The strategic alignment of resources with organizational objectives has resulted in measurable improvements in efficiency and effectiveness. Furthermore, the adoption of best practices has facilitated the development of sustainable solutions.",
    "The research findings clearly indicate that a paradigm shift is necessary to address the emerging challenges in the field. By embracing innovative approaches and fostering a culture of continuous learning, organizations can position themselves for long-term success. The empirical evidence supports the conclusion that proactive measures are more effective than reactive strategies.",
    "Moreover, the analysis highlights the importance of maintaining a balanced perspective when evaluating the potential impact of technological advancements. The integration of diverse viewpoints contributes to a more comprehensive understanding of the underlying dynamics. Consequently, decision-makers are better equipped to formulate effective policies.",
    "Кроме того, необходимо отметить, что применение передовых методологий значительно способствовало общему улучшению системных результатов. Внедрение комплексных стратегий обеспечивает извлечение пользы всеми заинтересованными сторонами из улучшенных рамок. Интеграция целостных подходов способствует достижению оптимальных результатов.",
    "Таким образом, вышеупомянутый анализ демонстрирует, что многоаспектный подход является необходимым для решения сложностей, присущих современным вызовам. Систематическая оценка показателей эффективности предоставляет ценные сведения для постоянного улучшения процессов.",
    "Darüber hinaus ist es wichtig festzustellen, dass die Anwendung fortschrittlicher Methoden erheblich zur allgemeinen Verbesserung der systemischen Ergebnisse beigetragen hat. Die Implementierung umfassender Strategien stellt sicher, dass alle Beteiligten von dem verbesserten Rahmen profitieren.",
    "En conclusión, el análisis mencionado anteriormente demuestra que un enfoque multifacético es esencial para abordar las complejidades inherentes a los desafíos modernos. La evaluación sistemática de métricas de rendimiento proporciona información valiosa para la mejora continua.",
    "De plus, il convient de noter que l'application de méthodologies avancées a contribué de manière significative à l'amélioration globale des résultats systémiques. L'intégration d'approches holistiques facilite l'obtention de résultats optimaux dans divers domaines.",
    "Inoltre, è importante notare che l'applicazione di metodologie avanzate ha contribuito in modo significativo al miglioramento complessivo dei risultati sistemici. L'implementazione di strategie comprensive assicura che tutte le parti interessate beneficino del quadro migliorato.",
    "Ponadto należy zauważyć, że zastosowanie zaawansowanych metodologii znacząco przyczyniło się do ogólnej poprawy wyników systemowych. Wdrożenie kompleksowych strategii zapewnia korzyści wszystkim zainteresowanym stronom.",
    "Além disso, é importante notar que a aplicação de metodologias avançadas contribuiu significativamente para a melhoria geral dos resultados sistêmicos. A integração de abordagens holísticas facilita a obtenção de resultados ótimos.",
    "Крім того, необхідно зазначити, що застосування передових методологій суттєво сприяло загальному покращенню системних результатів. Впровадження комплексних стратегій забезпечує отримання користі всіма зацікавленими сторонами.",
]

_HUMAN_TEXT_TEMPLATES: list[str] = [
    "So I was thinking about this the other day — you know how sometimes things just don't work the way you'd expect? Yeah, that happened again. Tried to fix the sink, ended up flooding half the kitchen. My wife wasn't thrilled, to say the least.",
    "Look, I'm not gonna pretend I have all the answers here. But from what I've seen working in this field for 15 years, the biggest mistake people make is overthinking it. Just start somewhere, make mistakes, learn from them. Simple as that.",
    "The meeting went sideways pretty fast. Tom brought up the budget issue again (surprise, surprise), and before you know it we're all arguing about whether to cut marketing or R&D. Nobody won that argument. We tabled it — again.",
    "Honestly? I think we're overcomplicating this. What if we just... asked the customers what they want? Revolutionary idea, I know. But half the time the solution is staring us right in the face and we're too busy building spreadsheets to notice.",
    "My grandmother always said — 'If you can't explain it simply, you don't understand it well enough.' She never went to college but she was smarter than most PhDs I've met. Life teaches you things no classroom can.",
    "Rain again today. Third day in a row. The garden's happy at least. But I had to cancel the barbecue we'd planned for weeks. Moved everything inside, crammed 20 people into the living room. It was actually more fun that way? Go figure.",
    "Знаешь, я долго думал над этим вопросом, и вот что понял — нет смысла гнаться за совершенством. Сделал как получилось, посмотрел что вышло, поправил. И так по кругу. Жизнь — она не по учебнику идёт.",
    "Да ладно тебе, не всё так плохо! Помнишь, как в прошлом году было? Вот это было действительно ужасно. А сейчас — ну подумаешь, не получилось с первого раза. Зато опыт какой!",
    "Also, ich sag mal so — manchmal muss man einfach machen und nicht so viel nachdenken. Klar, Planung ist wichtig und so, aber irgendwann muss man halt auch anfangen. Sonst sitzt man ewig rum und nix passiert.",
    "Mira, no soy experto en esto, pero lo que sí te puedo decir es que hay que tener paciencia. Mi abuelo siempre decía 'las cosas buenas llegan a los que saben esperar'. Suena cursi, pero es verdad.",
    "Écoute, je vais te dire un truc — ça fait 10 ans que je fais ça et j'ai toujours pas tout compris. C'est normal. Personne comprend tout. L'important c'est d'avancer, pas d'être parfait.",
    "Sai cosa ti dico? Alla fine quello che conta è la pratica, non la teoria. Ho letto mille libri sull'argomento ma la verità l'ho capita solo quando ho iniziato a fare le cose. Sbagliando, certo, ma facendo.",
    "Wiesz co, ja tam nie jestem jakimś ekspertem, ale jedno ci powiem — najważniejsze to nie poddawać się. Jak coś nie wychodzi, to trzeba spróbować inaczej. Proste? No właśnie nie zawsze.",
    "Olha, eu não vou mentir pra você — no começo foi difícil pra caramba. Mas com o tempo a gente vai pegando o jeito. O segredo é não desistir quando as coisas ficam complicadas.",
    "Слухай, я тобі скажу чесно — це не так просто, як здається. Але й не настільки складно, щоб здаватися. Головне — почати робити, а далі воно потроху само складається.",
]


def _augment_text(text: str, rng: random.Random) -> str:
    """Apply random augmentations to text for data diversity."""
    # Random sentence reordering
    if rng.random() < 0.3:
        sentences = re.split(r'(?<=[.!?])\s+', text)
        if len(sentences) > 2:
            rng.shuffle(sentences)
            text = " ".join(sentences)

    # Random word insertion
    if rng.random() < 0.2:
        filler_words = ["actually", "basically", "really", "quite", "perhaps",
                       "however", "meanwhile", "interestingly", "surprisingly"]
        words = text.split()
        if len(words) > 5:
            pos = rng.randint(1, len(words) - 1)
            words.insert(pos, rng.choice(filler_words))
            text = " ".join(words)

    # Random case variation
    if rng.random() < 0.1:
        sentences = re.split(r'(?<=[.!?])\s+', text)
        if sentences:
            idx = rng.randint(0, len(sentences) - 1)
            sentences[idx] = sentences[idx].lower()
            text = " ".join(sentences)

    return text


def _generate_mixed_text(ai_texts: list[str], human_texts: list[str],
                         rng: random.Random) -> tuple[str, float]:
    """Generate mixed AI/human text with interpolated label."""
    ratio = rng.random()
    if ratio < 0.3:
        # Mostly human
        base = rng.choice(human_texts)
        label = rng.uniform(0.0, 0.3)
    elif ratio < 0.7:
        # Mixed
        ai_sents = re.split(r'(?<=[.!?])\s+', rng.choice(ai_texts))
        human_sents = re.split(r'(?<=[.!?])\s+', rng.choice(human_texts))
        n_ai = rng.randint(1, max(1, len(ai_sents) // 2))
        n_human = rng.randint(1, max(1, len(human_sents) // 2))
        mixed = ai_sents[:n_ai] + human_sents[:n_human]
        rng.shuffle(mixed)
        base = " ".join(mixed)
        ai_frac = n_ai / max(n_ai + n_human, 1)
        label = 0.3 + ai_frac * 0.4
    else:
        # Mostly AI
        base = rng.choice(ai_texts)
        label = rng.uniform(0.7, 1.0)

    return _augment_text(base, rng), label


class TrainingDataGenerator:
    """Generate labeled training data for AI detection.

    Uses representative AI and human text templates with augmentation
    to create diverse training samples. Supports all 10 library languages.
    """

    def __init__(self, seed: int = 42) -> None:
        self.rng = random.Random(seed)
        self._ai_texts = list(_AI_TEXT_TEMPLATES)
        self._human_texts = list(_HUMAN_TEXT_TEMPLATES)

    def generate(
        self, n_samples: int = 5000
    ) -> list[tuple[Vec, float]]:
        """Generate training data as (feature_vector, label) pairs.

        Labels: 0.0 = human, 1.0 = AI.
        """
        from texthumanize.neural_detector import extract_features, normalize_features

        data: list[tuple[Vec, float]] = []
        n_pure_ai = n_samples // 4
        n_pure_human = n_samples // 4
        n_mixed = n_samples - n_pure_ai - n_pure_human

        logger.info("Generating %d training samples (%d AI, %d human, %d mixed)...",
                    n_samples, n_pure_ai, n_pure_human, n_mixed)

        # Pure AI texts
        for _i in range(n_pure_ai):
            text = _augment_text(self.rng.choice(self._ai_texts), self.rng)
            try:
                features = extract_features(text, "auto")
                norm = normalize_features(features)
                data.append((norm, self.rng.uniform(0.75, 1.0)))
            except Exception:
                continue

        # Pure human texts
        for _i in range(n_pure_human):
            text = _augment_text(self.rng.choice(self._human_texts), self.rng)
            try:
                features = extract_features(text, "auto")
                norm = normalize_features(features)
                data.append((norm, self.rng.uniform(0.0, 0.25)))
            except Exception:
                continue

        # Mixed texts
        for _i in range(n_mixed):
            text, label = _generate_mixed_text(
                self._ai_texts, self._human_texts, self.rng
            )
            try:
                features = extract_features(text, "auto")
                norm = normalize_features(features)
                data.append((norm, label))
            except Exception:
                continue

        logger.info("Generated %d training samples successfully.", len(data))
        return data


# ---------------------------------------------------------------------------
# LSTM Training (Backprop Through Time)
# ---------------------------------------------------------------------------

class LSTMTrainer:
    """Train a character-level LSTM language model via BPTT.

    Uses truncated BPTT with a configurable window size for efficiency.
    """

    def __init__(
        self,
        lstm: LSTMCell,
        embed_w: Mat,
        proj_w: Mat,
        proj_b: Vec,
        vocab_size: int,
        lr: float = 0.001,
        bptt_len: int = 50,
        clip_grad: float = 5.0,
    ) -> None:
        self.lstm = lstm
        self.embed_w = embed_w  # vocab_size x embed_dim
        self.proj_w = proj_w    # vocab_size x hidden_dim
        self.proj_b = proj_b    # vocab_size
        self.vocab_size = vocab_size
        self.optimizer = AdamOptimizer(lr=lr)
        self.bptt_len = bptt_len
        self.clip_grad = clip_grad

    def _clip(self, v: float) -> float:
        c = self.clip_grad
        return v if -c <= v <= c else (c if v > c else -c)

    def train_sequence(self, char_indices: list[int]) -> float:
        """Train on a character sequence. Returns average loss."""
        if len(char_indices) < 2:
            return 0.0

        hidden_dim = self.lstm.hidden_size
        embed_dim = len(self.embed_w[0]) if self.embed_w else 0
        vocab_size = self.vocab_size
        clip = self.clip_grad

        total_loss = 0.0
        n_steps = 0

        h = [0.0] * hidden_dim
        c = [0.0] * hidden_dim

        # Process in BPTT windows
        for start in range(0, len(char_indices) - 1, self.bptt_len):
            end = min(start + self.bptt_len, len(char_indices) - 1)
            window = char_indices[start:end + 1]

            if len(window) < 2:
                break

            # Forward pass with caching
            h_cache: list[Vec] = [list(h)]
            c_cache: list[Vec] = [list(c)]
            x_cache: list[Vec] = []
            prob_cache: list[Vec] = []
            targets: list[int] = []
            window_loss = 0.0

            for t in range(len(window) - 1):
                x = list(self.embed_w[window[t]])
                x_cache.append(x)

                h, c = self.lstm.forward(x, h, c)
                h_cache.append(list(h))
                c_cache.append(list(c))

                # Output logits
                logits = [
                    _dot(self.proj_w[v], h) + self.proj_b[v]
                    for v in range(vocab_size)
                ]
                log_probs = _log_softmax(logits)
                prob_cache.append(_softmax(logits))

                target = window[t + 1]
                targets.append(target)
                window_loss += -log_probs[target]
                n_steps += 1

            total_loss += window_loss
            seq_len = len(window) - 1
            inv_seq = 1.0 / seq_len

            # Backward pass (simplified BPTT)
            dh_next = [0.0] * hidden_dim
            dc_next = [0.0] * hidden_dim

            # Accumulate gradients for projection
            d_proj_w: Mat = [[0.0] * hidden_dim for _ in range(vocab_size)]
            d_proj_b: Vec = [0.0] * vocab_size
            d_embed: dict[int, Vec] = {}

            # Gate gradients accumulation
            combined_size = hidden_dim + embed_dim
            d_wf: Mat = [[0.0] * combined_size for _ in range(hidden_dim)]
            d_bf: Vec = [0.0] * hidden_dim
            d_wi: Mat = [[0.0] * combined_size for _ in range(hidden_dim)]
            d_bi: Vec = [0.0] * hidden_dim
            d_wg: Mat = [[0.0] * combined_size for _ in range(hidden_dim)]
            d_bg: Vec = [0.0] * hidden_dim
            d_wo: Mat = [[0.0] * combined_size for _ in range(hidden_dim)]
            d_bo: Vec = [0.0] * hidden_dim

            for t in range(seq_len - 1, -1, -1):
                target = targets[t]
                probs = prob_cache[t]
                h_t = h_cache[t + 1]
                h_prev = h_cache[t]
                c_t = c_cache[t + 1]
                c_prev = c_cache[t]
                x_t = x_cache[t]

                # Gradient of loss w.r.t output logits (softmax cross-entropy, scaled)
                d_logits = [p * inv_seq for p in probs]
                d_logits[target] -= inv_seq

                # Gradient w.r.t projection (only update top-k active logits for speed)
                for v in range(vocab_size):
                    dv = d_logits[v]
                    if abs(dv) < 1e-6:
                        continue
                    row = d_proj_w[v]
                    for d in range(hidden_dim):
                        row[d] += dv * h_t[d]
                    d_proj_b[v] += dv

                # Gradient w.r.t h_t from projection
                dh = list(dh_next)
                for d in range(hidden_dim):
                    s = 0.0
                    for v in range(vocab_size):
                        dv = d_logits[v]
                        if abs(dv) < 1e-6:
                            continue
                        s += dv * self.proj_w[v][d]
                    dh[d] += s

                # Backprop through LSTM cell
                combined = h_prev + x_t

                # Recompute gates
                f_gate = [_sigmoid(v) for v in _vecadd(_matvec(self.lstm.wf, combined), self.lstm.bf)]
                i_gate = [_sigmoid(v) for v in _vecadd(_matvec(self.lstm.wi, combined), self.lstm.bi)]
                g_gate = [_tanh(v) for v in _vecadd(_matvec(self.lstm.wg, combined), self.lstm.bg)]
                o_gate = [_sigmoid(v) for v in _vecadd(_matvec(self.lstm.wo, combined), self.lstm.bo)]

                # d_c from output
                tanh_c = [_tanh(ci) for ci in c_t]
                dc = [
                    dh[d] * o_gate[d] * (1 - tanh_c[d] ** 2) + dc_next[d]
                    for d in range(hidden_dim)
                ]

                # Gate deltas
                df = [dc[d] * c_prev[d] * f_gate[d] * (1 - f_gate[d]) for d in range(hidden_dim)]
                di = [dc[d] * g_gate[d] * i_gate[d] * (1 - i_gate[d]) for d in range(hidden_dim)]
                dg = [dc[d] * i_gate[d] * (1 - g_gate[d] ** 2) for d in range(hidden_dim)]
                do = [dh[d] * tanh_c[d] * o_gate[d] * (1 - o_gate[d]) for d in range(hidden_dim)]

                # Accumulate gate weight gradients (clipped)
                for d in range(hidden_dim):
                    df_d = df[d]
                    di_d = di[d]
                    dg_d = dg[d]
                    do_d = do[d]
                    for k in range(combined_size):
                        ck = combined[k]
                        d_wf[d][k] += df_d * ck
                        d_wi[d][k] += di_d * ck
                        d_wg[d][k] += dg_d * ck
                        d_wo[d][k] += do_d * ck
                    d_bf[d] += df_d
                    d_bi[d] += di_d
                    d_bg[d] += dg_d
                    d_bo[d] += do_d

                # Gradient w.r.t combined input
                d_combined = [0.0] * combined_size
                for k in range(combined_size):
                    s = 0.0
                    for d in range(hidden_dim):
                        s += (
                            self.lstm.wf[d][k] * df[d] +
                            self.lstm.wi[d][k] * di[d] +
                            self.lstm.wg[d][k] * dg[d] +
                            self.lstm.wo[d][k] * do[d]
                        )
                    d_combined[k] = s

                dh_next = d_combined[:hidden_dim]
                dx = d_combined[hidden_dim:]

                # Embedding gradient
                char_idx = window[t]
                if char_idx not in d_embed:
                    d_embed[char_idx] = [0.0] * embed_dim
                eg = d_embed[char_idx]
                for d in range(embed_dim):
                    eg[d] += dx[d]

                dc_next = [dc[d] * f_gate[d] for d in range(hidden_dim)]

            # Clip accumulated gradients
            def _clip_mat(m: Mat) -> Mat:
                for row in m:
                    for j in range(len(row)):
                        v = row[j]
                        if v > clip:
                            row[j] = clip
                        elif v < -clip:
                            row[j] = -clip
                return m

            def _clip_vec(vec: Vec) -> Vec:
                for j in range(len(vec)):
                    v = vec[j]
                    if v > clip:
                        vec[j] = clip
                    elif v < -clip:
                        vec[j] = -clip
                return vec

            _clip_mat(d_wf)
            _clip_vec(d_bf)
            _clip_mat(d_wi)
            _clip_vec(d_bi)
            _clip_mat(d_wg)
            _clip_vec(d_bg)
            _clip_mat(d_wo)
            _clip_vec(d_bo)
            _clip_mat(d_proj_w)
            _clip_vec(d_proj_b)

            # Apply gradients via Adam
            self.lstm.wf = self.optimizer.step_mat("lstm_wf", self.lstm.wf, d_wf)
            self.lstm.bf = self.optimizer.step_vec("lstm_bf", self.lstm.bf, d_bf)
            self.lstm.wi = self.optimizer.step_mat("lstm_wi", self.lstm.wi, d_wi)
            self.lstm.bi = self.optimizer.step_vec("lstm_bi", self.lstm.bi, d_bi)
            self.lstm.wg = self.optimizer.step_mat("lstm_wg", self.lstm.wg, d_wg)
            self.lstm.bg = self.optimizer.step_vec("lstm_bg", self.lstm.bg, d_bg)
            self.lstm.wo = self.optimizer.step_mat("lstm_wo", self.lstm.wo, d_wo)
            self.lstm.bo = self.optimizer.step_vec("lstm_bo", self.lstm.bo, d_bo)

            self.proj_w = self.optimizer.step_mat("proj_w", self.proj_w, d_proj_w)
            self.proj_b = self.optimizer.step_vec("proj_b", self.proj_b, d_proj_b)

            for char_idx, grad in d_embed.items():
                _clip_vec(grad)
                self.embed_w[char_idx] = self.optimizer.step_vec(
                    f"embed_{char_idx}", self.embed_w[char_idx], grad
                )

            # Detach hidden state
            h = [float(v) for v in h]
            c = [float(v) for v in c]

        return total_loss / max(n_steps, 1)


# ---------------------------------------------------------------------------
# Comprehensive training corpus for character-level LM
# ---------------------------------------------------------------------------

_LM_CORPUS: list[str] = [
    # English
    "The quick brown fox jumps over the lazy dog. Pack my box with five dozen liquor jugs.",
    "To be, or not to be, that is the question. Whether it is nobler in the mind to suffer the slings and arrows of outrageous fortune.",
    "It was the best of times, it was the worst of times, it was the age of wisdom, it was the age of foolishness.",
    "All happy families are alike; each unhappy family is unhappy in its own way.",
    "In the beginning God created the heavens and the earth. The earth was without form and void.",
    "The sun also rises. Ernest Hemingway wrote with short, declarative sentences. He believed in the power of simplicity.",
    "Technology has transformed our daily lives in ways we never imagined. From smartphones to artificial intelligence, the pace of change accelerates.",
    "Scientists discovered a remarkable pattern in the data. The correlation was undeniable, yet the mechanism remained elusive.",

    # Russian
    "Все счастливые семьи похожи друг на друга, каждая несчастливая семья несчастлива по-своему.",
    "В начале было Слово, и Слово было у Бога, и Слово было Бог.",
    "Мой дядя самых честных правил, когда не в шутку занемог, он уважать себя заставил и лучше выдумать не мог.",
    "Москва — столица России. Это крупнейший город страны с населением более 12 миллионов человек.",
    "Технологии меняют мир быстрее, чем когда-либо прежде. Искусственный интеллект проникает во все сферы жизни.",

    # Ukrainian
    "Реве та стогне Дніпр широкий, сердитий вітер завива, додолу верби гне високі, горами хвилю підійма.",
    "Київ — столиця та найбільше місто України. Місто розташоване на річці Дніпро.",
    "Українська мова — одна з найкрасивіших мов світу. Вона має багату історію та літературну традицію.",

    # German
    "Alle Menschen sind frei und gleich an Würde und Rechten geboren. Sie sind mit Vernunft und Gewissen begabt.",
    "Die Würde des Menschen ist unantastbar. Sie zu achten und zu schützen ist Verpflichtung aller staatlichen Gewalt.",
    "Berlin ist die Hauptstadt und der Regierungssitz der Bundesrepublik Deutschland.",

    # Spanish
    "En un lugar de la Mancha, de cuyo nombre no quiero acordarme, no ha mucho tiempo que vivía un hidalgo.",
    "Todos los seres humanos nacen libres e iguales en dignidad y derechos.",
    "La tecnología ha transformado nuestra vida cotidiana de maneras que nunca imaginamos.",

    # French
    "Longtemps, je me suis couché de bonne heure. Parfois, à peine ma bougie éteinte, mes yeux se fermaient si vite.",
    "Tous les êtres humains naissent libres et égaux en dignité et en droits.",
    "Paris est la capitale de la France et la ville la plus peuplée du pays.",

    # Italian
    "Nel mezzo del cammin di nostra vita mi ritrovai per una selva oscura, ché la diritta via era smarrita.",
    "Tutti gli esseri umani nascono liberi ed eguali in dignità e diritti.",
    "Roma è la capitale della Repubblica Italiana e capoluogo della città metropolitana.",

    # Polish
    "Litwo! Ojczyzno moja! Ty jesteś jak zdrowie. Ile cię trzeba cenić, ten tylko się dowie, kto cię stracił.",
    "Wszystkie istoty ludzkie rodzą się wolne i równe pod względem swej godności i swych praw.",
    "Warszawa jest stolicą i największym miastem Polski.",

    # Portuguese
    "Todas as pessoas nascem livres e iguais em dignidade e direitos.",
    "Lisboa é a capital e a maior cidade de Portugal.",
    "O Brasil é o maior país da América do Sul e o quinto maior do mundo.",

    # Turkish
    "Bütün insanlar hür, haysiyet ve haklar bakımından eşit doğarlar.",
    "İstanbul, Türkiye'nin en kalabalık şehri ve ülkenin ekonomik, tarihi ve kültürel merkezidir.",

    # Arabic
    "يولد جميع الناس أحراراً ومتساوين في الكرامة والحقوق.",
    "القاهرة هي عاصمة جمهورية مصر العربية وأكبر مدنها.",

    # Japanese
    "すべての人間は、生まれながらにして自由であり、かつ、尊厳と権利について平等である。",
    "東京は日本の首都であり、世界最大の都市圏の一つです。",

    # Korean
    "모든 인간은 태어날 때부터 자유로우며 그 존엄과 권리에 있어 동등하다.",
    "서울은 대한민국의 수도이자 최대 도시이다.",

    # Chinese
    "人人生而自由，在尊严和权利上一律平等。",
    "北京是中华人民共和国的首都，是全国的政治、文化、科技中心。",
]


# ---------------------------------------------------------------------------
# Main Trainer class
# ---------------------------------------------------------------------------

class Trainer:
    """Comprehensive training pipeline for TextHumanize neural components.

    Manages the complete training workflow:
    1. Data generation from templates + augmentation
    2. MLP detector training via backpropagation
    3. Character-level LSTM training via BPTT
    4. Weight export and compression

    Usage::

        trainer = Trainer(seed=42)
        trainer.generate_data(n_samples=5000)
        results = trainer.train_detector(epochs=50)
        lm_results = trainer.train_lm(epochs=20)
        trainer.export_weights("texthumanize/weights")
    """

    def __init__(self, seed: int = 42) -> None:
        self.seed = seed
        self.rng = random.Random(seed)
        self._train_data: list[tuple[Vec, float]] = []
        self._val_data: list[tuple[Vec, float]] = []
        self._net: FeedForwardNet | None = None
        self._training_log: list[dict[str, Any]] = []

    def generate_data(
        self,
        n_samples: int = 5000,
        val_split: float = 0.2,
    ) -> dict[str, int]:
        """Generate training and validation data."""
        gen = TrainingDataGenerator(seed=self.seed)
        all_data = gen.generate(n_samples)
        self.rng.shuffle(all_data)

        split_idx = int(len(all_data) * (1 - val_split))
        self._train_data = all_data[:split_idx]
        self._val_data = all_data[split_idx:]

        return {
            "total": len(all_data),
            "train": len(self._train_data),
            "val": len(self._val_data),
        }

    def train_detector(
        self,
        epochs: int = 50,
        lr: float = 0.001,
        weight_decay: float = 1e-4,
        verbose: bool = True,
    ) -> dict[str, Any]:
        """Train the MLP detector on generated data.

        Returns training results with accuracy and loss curves.
        """
        if not self._train_data:
            self.generate_data()

        from texthumanize.neural_engine import build_mlp

        # Build fresh network
        self._net = build_mlp(
            layer_sizes=[35, 64, 32, 1],
            activations=["relu", "relu", "linear"],
            seed=self.seed,
        )

        trainer = MLPTrainer(self._net, lr=lr, weight_decay=weight_decay)
        self._training_log = []

        best_val_acc = 0.0
        best_weights: dict[str, Any] | None = None
        patience = 10
        patience_counter = 0

        for epoch in range(epochs):
            train_loss = trainer.train_epoch(
                self._train_data, shuffle=True, seed=self.seed + epoch
            )
            val_metrics = trainer.evaluate(self._val_data)

            log_entry = {
                "epoch": epoch + 1,
                "train_loss": round(train_loss, 4),
                "val_loss": round(val_metrics["loss"], 4),
                "val_accuracy": round(val_metrics["accuracy"], 4),
                "val_f1": round(val_metrics["f1"], 4),
                "val_precision": round(val_metrics["precision"], 4),
                "val_recall": round(val_metrics["recall"], 4),
            }
            self._training_log.append(log_entry)

            if verbose and (epoch + 1) % 5 == 0:
                logger.info(
                    "Epoch %d/%d — train_loss=%.4f, val_acc=%.4f, val_f1=%.4f",
                    epoch + 1, epochs, train_loss,
                    val_metrics["accuracy"], val_metrics["f1"],
                )

            # Early stopping with best model save
            if val_metrics["accuracy"] > best_val_acc:
                best_val_acc = val_metrics["accuracy"]
                best_weights = self._net.to_config()
                patience_counter = 0
            else:
                patience_counter += 1
                if patience_counter >= patience:
                    logger.info("Early stopping at epoch %d", epoch + 1)
                    break

        # Restore best weights
        if best_weights is not None:
            self._net = FeedForwardNet.from_config(best_weights)

        final_metrics = trainer.evaluate(self._val_data)
        return {
            "epochs_trained": len(self._training_log),
            "best_val_accuracy": best_val_acc,
            "final_metrics": final_metrics,
            "training_log": self._training_log,
            "param_count": self._net.param_count if self._net else 0,
        }

    def train_lm(
        self,
        epochs: int = 20,
        lr: float = 0.002,
        verbose: bool = True,
    ) -> dict[str, Any]:
        """Train the character-level LSTM language model.

        Uses the built-in multilingual corpus for training.
        """
        from texthumanize.neural_lm import (
            _EMBED_DIM,
            _HIDDEN_DIM,
            _VOCAB_SIZE,
            _char_idx,
        )

        # Initialize fresh LSTM
        combined = _HIDDEN_DIM + _EMBED_DIM
        lstm = LSTMCell(
            input_size=_EMBED_DIM, hidden_size=_HIDDEN_DIM,
            wf=_he_init(combined, _HIDDEN_DIM, seed=100),
            bf=_zeros(_HIDDEN_DIM),
            wi=_he_init(combined, _HIDDEN_DIM, seed=200),
            bi=_zeros(_HIDDEN_DIM),
            wg=_he_init(combined, _HIDDEN_DIM, seed=300),
            bg=_zeros(_HIDDEN_DIM),
            wo=_he_init(combined, _HIDDEN_DIM, seed=400),
            bo=_zeros(_HIDDEN_DIM),
        )

        # Embedding and output projection
        rng = random.Random(self.seed)
        scale_e = 1.0 / math.sqrt(_EMBED_DIM)
        embed_w: Mat = [
            [rng.gauss(0, scale_e) for _ in range(_EMBED_DIM)]
            for _ in range(_VOCAB_SIZE)
        ]
        scale_p = 1.0 / math.sqrt(_HIDDEN_DIM)
        proj_w: Mat = [
            [rng.gauss(0, scale_p) for _ in range(_HIDDEN_DIM)]
            for _ in range(_VOCAB_SIZE)
        ]
        proj_b: Vec = [0.0] * _VOCAB_SIZE

        lm_trainer = LSTMTrainer(
            lstm=lstm, embed_w=embed_w, proj_w=proj_w, proj_b=proj_b,
            vocab_size=_VOCAB_SIZE, lr=lr, bptt_len=30,
        )

        # Prepare corpus — truncate texts for speed
        max_text_len = 120  # Limit to make pure-Python BPTT tractable
        corpus_texts = [t[:max_text_len] for t in _LM_CORPUS]
        training_log = []

        for epoch in range(epochs):
            rng_epoch = random.Random(self.seed + epoch)
            rng_epoch.shuffle(corpus_texts)

            epoch_loss = 0.0
            n_texts = 0

            for text in corpus_texts:
                indices = [_char_idx(ch) for ch in text]
                if len(indices) < 5:
                    continue
                loss = lm_trainer.train_sequence(indices)
                epoch_loss += loss
                n_texts += 1

            avg_loss = epoch_loss / max(n_texts, 1)
            training_log.append({
                "epoch": epoch + 1,
                "avg_loss": round(avg_loss, 4),
                "n_texts": n_texts,
            })

            if verbose:
                logger.info(
                    "LM Epoch %d/%d — avg_loss=%.4f (%d texts)",
                    epoch + 1, epochs, avg_loss, n_texts,
                )

        return {
            "epochs_trained": len(training_log),
            "training_log": training_log,
            "lstm": lstm,
            "embed_w": embed_w,
            "proj_w": proj_w,
            "proj_b": proj_b,
        }

    def export_weights(self, output_dir: str = "texthumanize/weights") -> dict[str, str]:
        """Export trained weights as compressed blobs.

        Creates:
        - detector_weights.json.zb85 — MLP weights
        - lm_weights.json.zb85 — LSTM + embedding + projection weights
        """
        os.makedirs(output_dir, exist_ok=True)
        exported = {}

        # Export detector weights
        if self._net is not None:
            config = self._net.to_config()
            blob = compress_weights(config)
            path = os.path.join(output_dir, "detector_weights.json.zb85")
            with open(path, "w") as f:
                f.write(blob)
            exported["detector"] = path
            logger.info("Exported detector weights: %s (%d bytes)", path, len(blob))

        return exported

    def export_lm_weights(
        self,
        lm_result: dict[str, Any],
        output_dir: str = "texthumanize/weights",
    ) -> str:
        """Export LSTM language model weights."""
        os.makedirs(output_dir, exist_ok=True)

        lstm = lm_result["lstm"]
        data = {
            "lstm": {
                "input_size": lstm.input_size,
                "hidden_size": lstm.hidden_size,
                "wf": lstm.wf, "bf": lstm.bf,
                "wi": lstm.wi, "bi": lstm.bi,
                "wg": lstm.wg, "bg": lstm.bg,
                "wo": lstm.wo, "bo": lstm.bo,
            },
            "embed_w": lm_result["embed_w"],
            "proj_w": lm_result["proj_w"],
            "proj_b": lm_result["proj_b"],
        }

        blob = compress_weights(data)
        path = os.path.join(output_dir, "lm_weights.json.zb85")
        with open(path, "w") as f:
            f.write(blob)
        logger.info("Exported LM weights: %s (%d bytes)", path, len(blob))
        return path
