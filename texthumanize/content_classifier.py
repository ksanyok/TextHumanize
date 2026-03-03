"""Content type classifier — determines text category for adaptive processing.

Classifies text into one of several categories:
- code: primarily source code (Python, JS, etc.)
- mixed_code: article/tutorial with embedded code blocks
- article: structured article with headings and paragraphs
- news: news-style writing (datelines, quotes, short paragraphs)
- tutorial: step-by-step guides, how-to content
- academic: formal academic/scientific text
- chat: informal/conversational text
- technical_doc: API docs, reference, specifications
- list_heavy: text dominated by bullet/numbered lists
- general: unclassified general text

The classifier is heuristic-based for speed (<2ms) and runs as the
very first pipeline stage to route processing appropriately.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from enum import Enum


class ContentType(Enum):
    """Enumeration of recognized content types."""
    CODE = "code"
    MIXED_CODE = "mixed_code"
    ARTICLE = "article"
    NEWS = "news"
    TUTORIAL = "tutorial"
    ACADEMIC = "academic"
    CHAT = "chat"
    TECHNICAL_DOC = "technical_doc"
    LIST_HEAVY = "list_heavy"
    GENERAL = "general"


@dataclass
class ContentProfile:
    """Detailed content analysis profile."""
    content_type: ContentType
    confidence: float  # 0.0 – 1.0
    scores: dict[str, float] = field(default_factory=dict)

    # Structural metadata
    code_block_ratio: float = 0.0      # fraction of text in code blocks
    heading_count: int = 0
    list_item_count: int = 0
    paragraph_count: int = 0
    avg_paragraph_length: float = 0.0  # words
    has_frontmatter: bool = False

    # Processing hints (used by pipeline router)
    protect_structure: bool = False     # headings, lists must be preserved
    protect_whitespace: bool = False    # indentation is semantic (code)
    allow_paraphrase: bool = True       # safe to paraphrase content
    allow_syntax_rewrite: bool = True   # safe to restructure sentences
    max_intensity_cap: int = 80         # upper bound on effective intensity


# ── Regex patterns ────────────────────────────────────────────
_CODE_BLOCK_RE = re.compile(r'```[\s\S]*?```|~~~[\s\S]*?~~~', re.MULTILINE)
_INDENTED_CODE_RE = re.compile(r'^(?:    |\t).+$', re.MULTILINE)
_HEADING_MD_RE = re.compile(r'^#{1,6}\s+.+$', re.MULTILINE)
_HEADING_HTML_RE = re.compile(r'<h[1-6][^>]*>.*?</h[1-6]>', re.IGNORECASE)
_BULLET_RE = re.compile(r'^\s*[-*•▸►]\s+.+$', re.MULTILINE)
_NUMBERED_RE = re.compile(r'^\s*\d+[.)]\s+.+$', re.MULTILINE)
_DATELINE_RE = re.compile(
    r'(?:^|\n)\s*(?:[A-Z]{2,}[\s,]+)?'
    r'(?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec|'
    r'Январ|Феврал|Март|Апрел|Ма[йя]|Июн|Июл|Август|Сентябр|Октябр|Ноябр|Декабр)'
    r'[\w,.\s]+\d{4}',
    re.IGNORECASE,
)
_QUOTE_ATTR_RE = re.compile(
    r'[«"""\']\s*[^«"""\']{10,}[«"""\']\s*[,—–-]\s*(?:сказал|заявил|said|told|according)',
    re.IGNORECASE,
)
_STEP_RE = re.compile(
    r'(?:^|\n)\s*(?:шаг|step|этап)\s*\d+|'
    r'(?:^|\n)\s*(?:во-первых|во-вторых|в-третьих|firstly|secondly|thirdly)|'
    r'(?:^|\n)\s*\d+\.\s+(?:Install|Set up|Create|Open|Run|Configure|Add|'
    r'Установ|Создай|Откр|Запуст|Настро|Добав)',
    re.IGNORECASE | re.MULTILINE,
)
_CITATION_RE = re.compile(
    r'\[\d+\]|'
    r'\([A-ZА-Я][a-zа-яёA-Za-z]+\s+et\s+al\.?\s*,?\s*\d{4}\)|'
    r'[A-ZА-Я][a-zа-яёA-Za-z]+\s+et\s+al\.\s*\(\d{4}\)|'
    r'\([A-ZА-Я][a-zа-яёA-Za-z]+(?:\s*(?:&|и|,|and)\s*[A-ZА-Я][a-zа-яёA-Za-z]+)*\s*,?\s*\d{4}\)|'
    r'\((?:и\s*др|и\s+другие)[.,]?\s*,?\s*\d{4}\)',
)
_ABSTRACT_RE = re.compile(
    r'(?:^|\n)\s*(?:abstract|аннотация|анотація|резюме)\s*[:.]',
    re.IGNORECASE,
)
_API_DOC_RE = re.compile(
    r'(?:Parameters|Returns|Raises|Args|Kwargs|Attributes|'
    r'Параметры|Возвращает|Аргументы)\s*[:\n]',
    re.IGNORECASE,
)
_FUNCTION_SIG_RE = re.compile(
    r'(?:def|function|func|fn|class|struct|interface|type)\s+\w+\s*\(',
)
_EMOJI_RE = re.compile(
    r'[\U0001F600-\U0001F650\U0001F680-\U0001F6FF'
    r'\U0001F900-\U0001F9FF\U0001FA00-\U0001FA6F'
    r'\U0001FA70-\U0001FAFF\U00002702-\U000027B0'
    r'\U0000FE00-\U0000FE0F\U0001F1E0-\U0001F1FF]',
)
# Code keywords across common languages
_CODE_KW_RE = re.compile(
    r'\b(?:def|class|import|from|return|if|elif|else|for|while|try|except|'
    r'function|const|let|var|async|await|export|require|'
    r'public|private|protected|static|void|int|string|bool|'
    r'func|struct|impl|trait|match|enum|'
    r'SELECT|FROM|WHERE|INSERT|UPDATE|DELETE|JOIN)\b'
)
_INLINE_CODE_RE = re.compile(r'`[^`\n]+`')


def classify(text: str, lang: str = "en") -> ContentProfile:
    """Classify text content type.

    Fast heuristic classifier (<2ms for typical texts).
    Runs as pipeline stage 0 to determine processing route.

    Args:
        text: Input text to classify.
        lang: Language code.

    Returns:
        ContentProfile with type, confidence, and processing hints.
    """
    if not text or len(text.strip()) < 20:
        return ContentProfile(
            content_type=ContentType.GENERAL,
            confidence=0.5,
        )

    text_len = max(len(text), 1)
    lines = text.split('\n')
    n_lines = max(len(lines), 1)
    words = text.split()
    n_words = max(len(words), 1)

    # ── Structural feature extraction ─────────────────────────
    # Code blocks
    code_blocks = _CODE_BLOCK_RE.findall(text)
    code_block_chars = sum(len(b) for b in code_blocks)
    code_block_ratio = code_block_chars / text_len

    # Indented code (outside fenced blocks)
    text_no_codeblocks = _CODE_BLOCK_RE.sub('', text)
    indented_lines = _INDENTED_CODE_RE.findall(text_no_codeblocks)
    indented_ratio = len(indented_lines) / n_lines

    # Code keywords
    code_kw_matches = _CODE_KW_RE.findall(text_no_codeblocks)
    code_kw_ratio = len(code_kw_matches) / n_words

    # Inline code
    inline_code = _INLINE_CODE_RE.findall(text)
    inline_code_ratio = len(inline_code) / n_words

    # Headings
    headings_md = _HEADING_MD_RE.findall(text)
    headings_html = _HEADING_HTML_RE.findall(text)
    heading_count = len(headings_md) + len(headings_html)

    # Lists
    bullets = _BULLET_RE.findall(text)
    numbered = _NUMBERED_RE.findall(text)
    list_items = len(bullets) + len(numbered)
    list_ratio = list_items / n_lines

    # Paragraphs (separated by blank lines)
    paragraphs = [p.strip() for p in re.split(r'\n\s*\n', text) if p.strip()]
    n_paragraphs = max(len(paragraphs), 1)
    avg_para_words = sum(len(p.split()) for p in paragraphs) / n_paragraphs

    # Sentences
    from texthumanize.sentence_split import split_sentences
    sentences = split_sentences(text, lang=lang)
    n_sentences = max(len(sentences), 1)
    avg_sent_words = n_words / n_sentences
    sent_lengths = [len(s.split()) for s in sentences]
    short_sents = sum(1 for sl in sent_lengths if sl < 8)
    short_sent_ratio = short_sents / n_sentences

    # ── Category-specific signals ─────────────────────────────
    scores: dict[str, float] = {}

    # === CODE score ===
    code_score = 0.0
    # Fenced code blocks are strong signal
    if code_block_ratio > 0.6:
        code_score += 0.7
    elif code_block_ratio > 0.3:
        code_score += 0.4

    # Lots of indented blocks + keywords = source code
    if indented_ratio > 0.4:
        code_score += 0.3
    if code_kw_ratio > 0.08:
        code_score += 0.3
    elif code_kw_ratio > 0.04:
        code_score += 0.15

    # Characters like {}, (), ;, => in high concentration
    brace_count = text.count('{') + text.count('}') + text.count(';')
    if brace_count / text_len > 0.02:
        code_score += 0.2

    scores['code'] = min(1.0, code_score)

    # === MIXED_CODE score (article/tutorial with code) ===
    mixed_score = 0.0
    if 0.05 < code_block_ratio < 0.6:
        mixed_score += 0.4
    if inline_code_ratio > 0.02:
        mixed_score += 0.2
    if heading_count >= 1 and code_block_ratio > 0.05:
        mixed_score += 0.2
    if list_items > 0 and code_block_ratio > 0.05:
        mixed_score += 0.1
    scores['mixed_code'] = min(1.0, mixed_score)

    # === ARTICLE score ===
    article_score = 0.0
    if heading_count >= 2:
        article_score += 0.3
    elif heading_count == 1:
        article_score += 0.15
    if n_paragraphs >= 3 and avg_para_words > 30:
        article_score += 0.3
    if 12 <= avg_sent_words <= 30:
        article_score += 0.2
    if list_items > 0 and list_ratio < 0.3:
        article_score += 0.1
    scores['article'] = min(1.0, article_score)

    # === NEWS score ===
    news_score = 0.0
    if _DATELINE_RE.search(text):
        news_score += 0.35
    quote_attrs = _QUOTE_ATTR_RE.findall(text)
    if quote_attrs:
        news_score += 0.25
    # News = short paragraphs
    if avg_para_words < 40 and n_paragraphs >= 3:
        news_score += 0.15
    # No headings typically (or just one)
    if heading_count <= 1:
        news_score += 0.1
    scores['news'] = min(1.0, news_score)

    # === TUTORIAL score ===
    tutorial_score = 0.0
    step_matches = _STEP_RE.findall(text)
    if step_matches:
        tutorial_score += 0.4
    if numbered and len(numbered) >= 3:
        tutorial_score += 0.2
    if heading_count >= 2:
        tutorial_score += 0.15
    # Imperative mood check (basic)
    imperative_words_en = {'install', 'create', 'open', 'run', 'add', 'set',
                           'click', 'type', 'select', 'copy', 'paste', 'go'}
    imperative_words_ru = {'установите', 'создайте', 'откройте', 'запустите',
                           'добавьте', 'настройте', 'выберите', 'скопируйте',
                           'нажмите', 'введите', 'перейдите'}
    lower_text = text.lower()
    imp_count = sum(1 for w in imperative_words_en | imperative_words_ru
                    if w in lower_text)
    if imp_count >= 3:
        tutorial_score += 0.2
    scores['tutorial'] = min(1.0, tutorial_score)

    # === ACADEMIC score ===
    academic_score = 0.0
    citations = _CITATION_RE.findall(text)
    if len(citations) >= 2:
        academic_score += 0.4
    elif len(citations) == 1:
        academic_score += 0.2
    if _ABSTRACT_RE.search(text):
        academic_score += 0.3
    if avg_sent_words > 20:
        academic_score += 0.15
    # Formal vocabulary signals
    formal_markers = {'furthermore', 'moreover', 'consequently', 'thus',
                      'hence', 'hereby', 'notwithstanding', 'aforementioned',
                      'кроме того', 'более того', 'следовательно', 'таким образом',
                      'вышеизложенное', 'нижеследующий'}
    formal_count = sum(1 for fm in formal_markers if fm in lower_text)
    if formal_count >= 3:
        academic_score += 0.15
    scores['academic'] = min(1.0, academic_score)

    # === CHAT score ===
    chat_score = 0.0
    emoji_count = len(_EMOJI_RE.findall(text))
    if emoji_count >= 2:
        chat_score += 0.3
    elif emoji_count == 1:
        chat_score += 0.15
    if short_sent_ratio > 0.6:
        chat_score += 0.25
    if avg_sent_words < 10:
        chat_score += 0.2
    # Exclamations and questions
    excl_rate = text.count('!') / text_len
    quest_rate = text.count('?') / text_len
    if excl_rate > 0.005 or quest_rate > 0.005:
        chat_score += 0.15
    # Short total length
    if n_words < 100:
        chat_score += 0.1
    scores['chat'] = min(1.0, chat_score)

    # === TECHNICAL_DOC score ===
    tech_score = 0.0
    if _API_DOC_RE.search(text):
        tech_score += 0.35
    func_sigs = _FUNCTION_SIG_RE.findall(text_no_codeblocks)
    if len(func_sigs) >= 2:
        tech_score += 0.25
    if inline_code_ratio > 0.03:
        tech_score += 0.15
    if heading_count >= 3:
        tech_score += 0.1
    scores['technical_doc'] = min(1.0, tech_score)

    # === LIST_HEAVY score ===
    list_score = 0.0
    if list_ratio > 0.4:
        list_score += 0.5
    elif list_ratio > 0.25:
        list_score += 0.3
    if list_items >= 5:
        list_score += 0.2
    scores['list_heavy'] = min(1.0, list_score)

    # === GENERAL score (baseline) ===
    scores['general'] = 0.15  # low baseline — prefer specific types

    # ── Winner selection ──────────────────────────────────────
    best_type = max(scores, key=scores.get)  # type: ignore[arg-type]
    best_score = scores[best_type]

    content_type = ContentType(best_type)

    # Confidence: best score, penalized if tie is close
    sorted_scores = sorted(scores.values(), reverse=True)
    if len(sorted_scores) >= 2:
        gap = sorted_scores[0] - sorted_scores[1]
        confidence = min(1.0, best_score * 0.6 + gap * 0.4 + 0.1)
    else:
        confidence = min(1.0, best_score)

    # ── Build profile with processing hints ───────────────────
    profile = ContentProfile(
        content_type=content_type,
        confidence=confidence,
        scores=scores,
        code_block_ratio=code_block_ratio,
        heading_count=heading_count,
        list_item_count=list_items,
        paragraph_count=n_paragraphs,
        avg_paragraph_length=avg_para_words,
    )

    # Set processing hints based on content type
    _apply_processing_hints(profile, content_type)

    return profile


def _apply_processing_hints(profile: ContentProfile, ct: ContentType) -> None:
    """Set processing hints on the profile based on detected content type."""

    if ct == ContentType.CODE:
        profile.protect_structure = True
        profile.protect_whitespace = True
        profile.allow_paraphrase = False
        profile.allow_syntax_rewrite = False
        profile.max_intensity_cap = 20  # very light — comments only

    elif ct == ContentType.MIXED_CODE:
        profile.protect_structure = True
        profile.protect_whitespace = True
        profile.allow_paraphrase = True   # prose portions only
        profile.allow_syntax_rewrite = True
        profile.max_intensity_cap = 60

    elif ct == ContentType.ARTICLE:
        profile.protect_structure = True  # headings, lists
        profile.protect_whitespace = False
        profile.allow_paraphrase = True
        profile.allow_syntax_rewrite = True
        profile.max_intensity_cap = 80

    elif ct == ContentType.NEWS:
        profile.protect_structure = True
        profile.protect_whitespace = False
        profile.allow_paraphrase = True
        profile.allow_syntax_rewrite = True
        profile.max_intensity_cap = 70  # preserve factual precision

    elif ct == ContentType.TUTORIAL:
        profile.protect_structure = True  # steps must stay ordered
        profile.protect_whitespace = False
        profile.allow_paraphrase = True
        profile.allow_syntax_rewrite = False  # don't rewrite imperative steps
        profile.max_intensity_cap = 65

    elif ct == ContentType.ACADEMIC:
        profile.protect_structure = True
        profile.protect_whitespace = False
        profile.allow_paraphrase = True
        profile.allow_syntax_rewrite = False  # preserve register
        profile.max_intensity_cap = 55

    elif ct == ContentType.CHAT:
        profile.protect_structure = False
        profile.protect_whitespace = False
        profile.allow_paraphrase = True
        profile.allow_syntax_rewrite = True
        profile.max_intensity_cap = 80

    elif ct == ContentType.TECHNICAL_DOC:
        profile.protect_structure = True
        profile.protect_whitespace = True
        profile.allow_paraphrase = True
        profile.allow_syntax_rewrite = False
        profile.max_intensity_cap = 50

    elif ct == ContentType.LIST_HEAVY:
        profile.protect_structure = True
        profile.protect_whitespace = False
        profile.allow_paraphrase = True
        profile.allow_syntax_rewrite = False
        profile.max_intensity_cap = 65

    else:  # GENERAL
        profile.protect_structure = False
        profile.protect_whitespace = False
        profile.allow_paraphrase = True
        profile.allow_syntax_rewrite = True
        profile.max_intensity_cap = 80
