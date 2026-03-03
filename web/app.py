"""TextHumanize — Streamlit Web Interface.

Запуск:
    streamlit run web/app.py

Или через CLI:
    python -m texthumanize web
"""
from __future__ import annotations

import sys
import os
import time

# Ensure the project root is on the path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import streamlit as st

st.set_page_config(
    page_title="TextHumanize",
    page_icon="✍️",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ── CSS ──────────────────────────────────────────────────
st.markdown("""
<style>
    .main-header { font-size: 2.2rem; font-weight: 700; margin-bottom: 0.5rem; }
    .sub-header  { color: #888; margin-bottom: 1.5rem; }
    .metric-card {
        background: #f8f9fa; border-radius: 8px; padding: 1rem;
        text-align: center; border: 1px solid #e0e0e0;
    }
    .metric-value { font-size: 1.8rem; font-weight: 700; }
    .metric-label { font-size: 0.85rem; color: #666; }
    .score-high   { color: #e53e3e; }
    .score-medium { color: #d69e2e; }
    .score-low    { color: #38a169; }
    .diff-text ins { background: #c6f6d5; text-decoration: none; }
    .diff-text del { background: #fed7d7; text-decoration: line-through; }
    div[data-testid="stTextArea"] textarea { font-size: 1rem; }
</style>
""", unsafe_allow_html=True)


# ── Imports ──────────────────────────────────────────────
@st.cache_resource
def load_texthumanize():
    """Lazy-load TextHumanize to avoid import overhead on every rerun."""
    import texthumanize as th
    from texthumanize.lang import LANGUAGES
    return th, LANGUAGES


th, LANGUAGES = load_texthumanize()

# ── Sidebar ──────────────────────────────────────────────
with st.sidebar:
    st.markdown("## ⚙️ Настройки")

    LANG_NAMES = {
        "auto": "🌐 Авто-определение",
        "en": "🇬🇧 English", "ru": "🇷🇺 Русский", "uk": "🇺🇦 Українська",
        "de": "🇩🇪 Deutsch", "fr": "🇫🇷 Français", "es": "🇪🇸 Español",
        "it": "🇮🇹 Italiano", "pl": "🇵🇱 Polski", "pt": "🇵🇹 Português",
        "nl": "🇳🇱 Nederlands", "sv": "🇸🇪 Svenska", "cs": "🇨🇿 Čeština",
        "ro": "🇷🇴 Română", "hu": "🇭🇺 Magyar", "da": "🇩🇰 Dansk",
        "ar": "🇸🇦 العربية", "zh": "🇨🇳 中文", "ja": "🇯🇵 日本語",
        "ko": "🇰🇷 한국어", "tr": "🇹🇷 Türkçe",
        "hi": "🇮🇳 हिन्दी", "vi": "🇻🇳 Tiếng Việt", "th": "🇹🇭 ไทย",
        "id": "🇮🇩 Bahasa Indonesia", "he": "🇮🇱 עברית",
    }
    lang_options = ["auto"] + sorted(LANGUAGES.keys())
    lang = st.selectbox(
        "Язык текста",
        lang_options,
        format_func=lambda x: LANG_NAMES.get(x, x.upper()),
    )

    st.markdown("---")

    mode = st.radio(
        "Режим",
        ["🔍 Детекция AI", "✍️ Гуманизация", "🛡️ PHANTOM™", "⚡ ASH™"],
        index=1,
    )

    if mode in ["✍️ Гуманизация", "🛡️ PHANTOM™", "⚡ ASH™"]:
        intensity = st.slider("Интенсивность", 10, 100, 60, step=5)
        profile = st.selectbox(
            "Профиль",
            ["general", "chat", "web", "seo", "docs", "formal"],
            index=0,
        )
    else:
        intensity = 60
        profile = "general"

    st.markdown("---")
    st.markdown("### 📊 О проекте")
    st.markdown(f"**TextHumanize v{th.__version__}**")
    st.markdown(f"Языков: **{len(LANGUAGES)}**")
    st.markdown("Pipeline: **22 этапа**")
    st.markdown("MLP: **50,433 параметра**")

# ── Main Area ────────────────────────────────────────────
st.markdown('<div class="main-header">✍️ TextHumanize</div>', unsafe_allow_html=True)
st.markdown('<div class="sub-header">AI текст → человеческий текст. Локально, без API.</div>', unsafe_allow_html=True)

# Input
text = st.text_area(
    "Вставьте текст для обработки:",
    height=200,
    placeholder="Artificial intelligence has revolutionized numerous industries...",
)

# Action button
col_btn1, col_btn2, col_btn3 = st.columns([1, 1, 4])
with col_btn1:
    run_btn = st.button("🚀 Запустить", type="primary", use_container_width=True)
with col_btn2:
    clear_btn = st.button("🗑️ Очистить", use_container_width=True)

if clear_btn:
    st.rerun()

if run_btn and text.strip():
    effective_lang = lang if lang != "auto" else "auto"

    # ── Detection Mode ──
    if mode == "🔍 Детекция AI":
        with st.spinner("Анализ текста..."):
            t0 = time.perf_counter()
            result = th.detect_ai(text, lang=effective_lang)
            elapsed = time.perf_counter() - t0

        score = result.get("combined_score", 0)
        verdict = result.get("verdict", "unknown")
        confidence = result.get("confidence", 0)

        # Score display
        score_class = "score-high" if score > 0.55 else ("score-medium" if score > 0.34 else "score-low")
        verdict_emoji = "🤖" if verdict == "ai" else ("🔀" if verdict == "mixed" else "👤")

        st.markdown("---")
        col1, col2, col3, col4 = st.columns(4)
        with col1:
            st.markdown(f"""<div class="metric-card">
                <div class="metric-value {score_class}">{score:.0%}</div>
                <div class="metric-label">AI Вероятность</div>
            </div>""", unsafe_allow_html=True)
        with col2:
            st.markdown(f"""<div class="metric-card">
                <div class="metric-value">{verdict_emoji} {verdict}</div>
                <div class="metric-label">Вердикт</div>
            </div>""", unsafe_allow_html=True)
        with col3:
            st.markdown(f"""<div class="metric-card">
                <div class="metric-value">{confidence:.0%}</div>
                <div class="metric-label">Уверенность</div>
            </div>""", unsafe_allow_html=True)
        with col4:
            st.markdown(f"""<div class="metric-card">
                <div class="metric-value">{elapsed*1000:.0f}мс</div>
                <div class="metric-label">Время</div>
            </div>""", unsafe_allow_html=True)

        # Detailed metrics
        metrics = result.get("metrics", {})
        if metrics:
            st.markdown("### 📊 Детальные метрики")
            metrics_data = {
                "Энтропия": metrics.get("entropy", 0),
                "Burstiness": metrics.get("burstiness", 0),
                "Лексика": metrics.get("vocabulary", 0),
                "Zipf": metrics.get("zipf", 0),
                "Стилометрия": metrics.get("stylometry", 0),
                "AI-паттерны": metrics.get("ai_patterns", 0),
                "Пунктуация": metrics.get("punctuation", 0),
                "Когерентность": metrics.get("coherence", 0),
                "Грамматика": metrics.get("grammar_perfection", 0),
                "Начала предл.": metrics.get("opening_diversity", 0),
                "Читаемость": metrics.get("readability_consistency", 0),
                "Ритм": metrics.get("rhythm", 0),
            }

            cols = st.columns(4)
            for i, (name, val) in enumerate(metrics_data.items()):
                with cols[i % 4]:
                    bar_color = "#e53e3e" if val > 0.55 else ("#d69e2e" if val > 0.35 else "#38a169")
                    st.markdown(f"**{name}**: {val:.0%}")
                    st.progress(val)

        # Component scores
        heuristic = result.get("heuristic_score", 0)
        stat = result.get("stat_probability")
        neural = result.get("neural_probability")
        st.markdown("### 🧠 Компоненты ансамбля")
        c1, c2, c3 = st.columns(3)
        with c1:
            st.metric("Эвристический", f"{heuristic:.0%}")
        with c2:
            st.metric("Статистический", f"{stat:.0%}" if stat is not None else "N/A")
        with c3:
            st.metric("Нейросеть (MLP)", f"{neural:.0%}" if neural is not None else "N/A")

    # ── Humanization Mode ──
    elif mode == "✍️ Гуманизация":
        with st.spinner("Гуманизация текста..."):
            t0 = time.perf_counter()
            result = th.humanize(text, lang=effective_lang, intensity=intensity, profile=profile)
            elapsed = time.perf_counter() - t0

        st.markdown("---")

        # Metrics row
        col1, col2, col3, col4 = st.columns(4)
        with col1:
            st.metric("Изменение", f"{result.change_ratio:.0%}")
        with col2:
            st.metric("Качество", f"{result.quality_score:.0%}")
        with col3:
            st.metric("Язык", result.lang.upper())
        with col4:
            st.metric("Время", f"{elapsed:.1f}с")

        # Result text
        st.markdown("### 📝 Результат")
        st.text_area("Обработанный текст:", value=result.text, height=200)

        # AI score before/after
        ai_before = result.metrics_before.get("artificiality_score", 0)
        ai_after = result.metrics_after.get("artificiality_score", 0)
        st.markdown("### 📉 AI Score")
        c1, c2, c3 = st.columns(3)
        with c1:
            st.metric("До обработки", f"{ai_before:.0f}%")
        with c2:
            st.metric("После обработки", f"{ai_after:.0f}%")
        with c3:
            drop = ai_before - ai_after
            st.metric("Снижение", f"−{drop:.0f}%", delta=f"-{drop:.0f}%")

        # Changes log
        if result.changes:
            with st.expander(f"📋 Журнал изменений ({len(result.changes)} шагов)"):
                for change in result.changes[:50]:
                    desc = change.get("description", str(change))
                    st.markdown(f"- {desc}")

    # ── PHANTOM™ Mode ──
    elif mode == "🛡️ PHANTOM™":
        with st.spinner("PHANTOM™ обработка..."):
            t0 = time.perf_counter()
            result = th.phantom_humanize(text, lang=effective_lang, intensity=intensity)
            elapsed = time.perf_counter() - t0

        st.markdown("---")
        col1, col2, col3 = st.columns(3)
        with col1:
            st.metric("Язык", result.lang.upper())
        with col2:
            ops = len(result.operations) if hasattr(result, 'operations') else 0
            st.metric("Операций", str(ops))
        with col3:
            st.metric("Время", f"{elapsed:.1f}с")

        st.markdown("### 📝 Результат PHANTOM™")
        st.text_area("Обработанный текст:", value=result.text, height=200)

        # Detection before/after
        with st.spinner("Проверка детекции..."):
            det_before = th.detect_ai(text, lang=effective_lang)
            det_after = th.detect_ai(result.text, lang=effective_lang)
        score_before = det_before.get("combined_score", 0)
        score_after = det_after.get("combined_score", 0)
        drop = (score_before - score_after) * 100

        c1, c2, c3 = st.columns(3)
        with c1:
            st.metric("AI до", f"{score_before:.0%}")
        with c2:
            st.metric("AI после", f"{score_after:.0%}")
        with c3:
            st.metric("Снижение", f"−{drop:.0f}%", delta=f"-{drop:.0f}%")

    # ── ASH™ Mode ──
    elif mode == "⚡ ASH™":
        with st.spinner("ASH™ обработка..."):
            t0 = time.perf_counter()
            result = th.ash_humanize(text, lang=effective_lang, intensity=intensity)
            elapsed = time.perf_counter() - t0

        st.markdown("---")
        col1, col2, col3 = st.columns(3)
        with col1:
            st.metric("Язык", result.lang.upper())
        with col2:
            n_ops = len(result.changes) if hasattr(result, 'changes') else 0
            st.metric("Изменений", str(n_ops))
        with col3:
            st.metric("Время", f"{elapsed:.1f}с")

        st.markdown("### 📝 Результат ASH™")
        st.text_area("Обработанный текст:", value=result.text, height=200)

        # Detection
        with st.spinner("Проверка детекции..."):
            det_before = th.detect_ai(text, lang=effective_lang)
            det_after = th.detect_ai(result.text, lang=effective_lang)
        score_before = det_before.get("combined_score", 0)
        score_after = det_after.get("combined_score", 0)
        drop = (score_before - score_after) * 100

        c1, c2, c3 = st.columns(3)
        with c1:
            st.metric("AI до", f"{score_before:.0%}")
        with c2:
            st.metric("AI после", f"{score_after:.0%}")
        with c3:
            st.metric("Снижение", f"−{drop:.0f}%", delta=f"-{drop:.0f}%")

elif run_btn:
    st.warning("⚠️ Пожалуйста, вставьте текст для обработки.")

# ── Footer ───────────────────────────────────────────────
st.markdown("---")
st.markdown(
    f"<div style='text-align: center; color: #aaa; font-size: 0.85rem;'>"
    f"TextHumanize v{th.__version__} • {len(LANGUAGES)} языков • "
    f"<a href='https://github.com/TextHumanize' style='color: #888;'>GitHub</a>"
    f"</div>",
    unsafe_allow_html=True,
)
