#!/usr/bin/env python3
"""Скачивание бесплатных датасетов для обучения AI-детектора.

Датасеты:
  1. HC3 (Human ChatGPT Comparison) — ~24K пар (HuggingFace API)
  2. Ghostbuster — ~10-15K текстов (GitHub sparse clone)
  3. Wikipedia — случайные сниппеты (REST API)
  4. Пользовательские JSONL-файлы

Использование::

    # Скачать всё
    python scripts/download_training_data.py

    # Только HC3
    python scripts/download_training_data.py --dataset hc3

    # Только Ghostbuster
    python scripts/download_training_data.py --dataset ghostbuster

    # Импорт пользовательских данных из MD файла
    python scripts/download_training_data.py --import-file docs/TRAINING_DATA_PROMPT.md

    # Объединить и показать статистику
    python scripts/download_training_data.py --merge --stats
"""

from __future__ import annotations

import argparse
import json
import os
import shutil
import subprocess
import sys
import tempfile
import time
import urllib.error
import urllib.request

# ---------------------------------------------------------------------------
# Конфигурация
# ---------------------------------------------------------------------------

OUTPUT_DIR = "data"

# HC3 на HuggingFace
_HF_HC3_URL = (
    "https://datasets-server.huggingface.co/rows"
    "?dataset=Hello-SimpleAI/HC3"
    "&config=all"
    "&split=train"
    "&offset={offset}"
    "&length={length}"
)
_HF_CHUNK = 100  # макс. строк за запрос

# Ghostbuster на GitHub
_GHOSTBUSTER_REPO = "https://github.com/vivek3141/ghostbuster-data.git"

# Какие папки нужны из Ghostbuster (без logprobs)
_GHOSTBUSTER_DIRS = [
    # Эссе
    "essay/human",       # label=0.0
    "essay/gpt",         # label=1.0
    "essay/claude",      # label=1.0
    "essay/gpt_prompt1", # label=1.0
    "essay/gpt_prompt2", # label=1.0
    # Creative Writing (Writing Prompts)
    "wp/human",          # label=0.0
    "wp/gpt",            # label=1.0
    "wp/claude",         # label=1.0
    "wp/gpt_prompt1",    # label=1.0
    "wp/gpt_prompt2",    # label=1.0
    # Новости (Reuters)
    "reuter/human",      # label=0.0
    "reuter/gpt",        # label=1.0
    "reuter/claude",     # label=1.0
    "reuter/gpt_prompt1",# label=1.0
    "reuter/gpt_prompt2",# label=1.0
    # Другие человеческие тексты
    "other/bawe",        # label=0.0, British Academic Written English
    "other/ets",         # label=0.0, ETS essays
    "other/gptzero",     # human+gpt subfolders
    "other/undetectable", # label=1.0, тексты обходящие детекторы
]

# Маппинг путей → (label, source, domain)
_LABEL_MAP: dict[str, tuple[float, str, str]] = {
    # Essay
    "essay/human":       (0.0, "ghostbuster_human",        "essay"),
    "essay/gpt":         (1.0, "ghostbuster_gpt",          "essay"),
    "essay/claude":      (1.0, "ghostbuster_claude",       "essay"),
    "essay/gpt_prompt1": (1.0, "ghostbuster_gpt_prompt1",  "essay"),
    "essay/gpt_prompt2": (1.0, "ghostbuster_gpt_prompt2",  "essay"),
    # WP
    "wp/human":          (0.0, "ghostbuster_human",        "creative"),
    "wp/gpt":            (1.0, "ghostbuster_gpt",          "creative"),
    "wp/claude":         (1.0, "ghostbuster_claude",       "creative"),
    "wp/gpt_prompt1":    (1.0, "ghostbuster_gpt_prompt1",  "creative"),
    "wp/gpt_prompt2":    (1.0, "ghostbuster_gpt_prompt2",  "creative"),
    # Reuters
    "reuter/human":      (0.0, "ghostbuster_human",        "news"),
    "reuter/gpt":        (1.0, "ghostbuster_gpt",          "news"),
    "reuter/claude":     (1.0, "ghostbuster_claude",       "news"),
    "reuter/gpt_prompt1":(1.0, "ghostbuster_gpt_prompt1",  "news"),
    "reuter/gpt_prompt2":(1.0, "ghostbuster_gpt_prompt2",  "news"),
    # Other human
    "other/bawe":        (0.0, "ghostbuster_bawe",         "academic"),
    "other/ets":         (0.0, "ghostbuster_ets",          "essay"),
    "other/gptzero/human":(0.0,"ghostbuster_gptzero_human","mixed"),
    "other/gptzero/gpt": (1.0, "ghostbuster_gptzero_gpt",  "mixed"),
    "other/undetectable":(1.0, "ghostbuster_undetectable",  "evasion"),
}


# ---------------------------------------------------------------------------
# HC3 (HuggingFace API)
# ---------------------------------------------------------------------------

def download_hc3(output_dir: str, max_samples: int = 50000) -> str:
    """Скачать HC3 датасет через HuggingFace API.

    Содержит пары human/chatgpt ответов на вопросы.
    ~24K строк → ~40-48K текстов (человек + ChatGPT).
    """
    os.makedirs(output_dir, exist_ok=True)
    outpath = os.path.join(output_dir, "hc3_training.jsonl")

    print("=" * 60)
    print("  СКАЧИВАНИЕ HC3 (Human ChatGPT Comparison)")
    print("  Источник: huggingface.co/datasets/Hello-SimpleAI/HC3")
    print(f"  Макс. семплов: {max_samples}")
    print("=" * 60)

    total = 0
    n_human = 0
    n_ai = 0
    offset = 0
    errors = 0

    with open(outpath, "w", encoding="utf-8") as fout:
        while total < max_samples:
            url = _HF_HC3_URL.format(offset=offset, length=_HF_CHUNK)
            try:
                req = urllib.request.Request(url)
                req.add_header(
                    "User-Agent",
                    "TextHumanize/0.26 (training-data-download)",
                )
                with urllib.request.urlopen(req, timeout=30) as resp:
                    data = json.loads(resp.read().decode("utf-8"))
            except Exception as e:
                errors += 1
                if errors >= 5:
                    print(f"  Слишком много ошибок ({errors}), останавливаюсь.")
                    break
                print(f"  Ошибка на offset={offset}: {e}")
                time.sleep(2)
                continue

            rows = data.get("rows", [])
            if not rows:
                print(f"  Данных больше нет (offset={offset})")
                break

            for row_wrapper in rows:
                row = row_wrapper.get("row", {})

                # Human ответы → label=0.0
                human_answers = row.get("human_answers", [])
                for ans in human_answers:
                    if isinstance(ans, str) and len(ans.strip()) > 50:
                        obj = {
                            "text": ans.strip(),
                            "label": 0.0,
                            "lang": "en",
                            "source": "hc3_human",
                            "domain": "qa",
                        }
                        fout.write(json.dumps(obj, ensure_ascii=False) + "\n")
                        total += 1
                        n_human += 1

                # ChatGPT ответы → label=1.0
                chatgpt_answers = row.get("chatgpt_answers", [])
                for ans in chatgpt_answers:
                    if isinstance(ans, str) and len(ans.strip()) > 50:
                        obj = {
                            "text": ans.strip(),
                            "label": 1.0,
                            "lang": "en",
                            "source": "hc3_chatgpt",
                            "domain": "qa",
                        }
                        fout.write(json.dumps(obj, ensure_ascii=False) + "\n")
                        total += 1
                        n_ai += 1

                if total >= max_samples:
                    break

            offset += _HF_CHUNK
            errors = 0  # сброс на успехе
            if offset % 500 == 0 or total >= max_samples:
                print(f"  Скачано: {total} (human={n_human}, ai={n_ai}, offset={offset})")

    print(f"\n  Итого: {total} семплов -> {outpath}")
    print(f"  Human: {n_human}, AI: {n_ai}")
    return outpath


# ---------------------------------------------------------------------------
# Ghostbuster (GitHub sparse clone)
# ---------------------------------------------------------------------------

def download_ghostbuster(output_dir: str, max_per_dir: int = 1000) -> str:
    """Скачать Ghostbuster dataset через git sparse-checkout.

    Домены: эссе, creative writing, новости, академические тексты.
    ~10-15K текстов: human + GPT + Claude.
    """
    os.makedirs(output_dir, exist_ok=True)
    outpath = os.path.join(output_dir, "ghostbuster_training.jsonl")

    print("=" * 60)
    print("  СКАЧИВАНИЕ GHOSTBUSTER")
    print("  Источник: github.com/vivek3141/ghostbuster-data")
    print(f"  Макс. файлов на директорию: {max_per_dir}")
    print("=" * 60)

    # Проверяем наличие git
    if shutil.which("git") is None:
        print("  ОШИБКА: git не найден. Установите git и попробуйте снова.")
        return ""

    # Создаём временную директорию для клона
    tmpdir = tempfile.mkdtemp(prefix="ghostbuster_")
    clone_dir = os.path.join(tmpdir, "ghostbuster-data")

    try:
        # Sparse clone — скачиваем только нужные папки
        print("  Клонирование (sparse checkout)...")
        subprocess.run(
            [
                "git", "clone",
                "--depth", "1",
                "--filter=blob:none",
                "--sparse",
                _GHOSTBUSTER_REPO,
                clone_dir,
            ],
            capture_output=True,
            text=True,
            check=True,
            timeout=120,
        )

        # Настраиваем sparse-checkout
        print("  Настройка sparse-checkout (скачиваю нужные папки)...")
        subprocess.run(
            ["git", "sparse-checkout", "init", "--cone"],
            cwd=clone_dir,
            capture_output=True,
            text=True,
            check=True,
        )
        subprocess.run(
            ["git", "sparse-checkout", "set"] + _GHOSTBUSTER_DIRS,
            cwd=clone_dir,
            capture_output=True,
            text=True,
            check=True,
            timeout=600,
        )

        # Обрабатываем файлы
        total = 0
        n_human = 0
        n_ai = 0

        with open(outpath, "w", encoding="utf-8") as fout:
            for gb_dir, (label, source, domain) in _LABEL_MAP.items():
                dir_path = os.path.join(clone_dir, gb_dir)
                if not os.path.isdir(dir_path):
                    print(f"  Пропуск: {gb_dir} (не найдена)")
                    continue

                count = 0
                for fname in sorted(os.listdir(dir_path)):
                    if not fname.endswith(".txt"):
                        continue
                    if count >= max_per_dir:
                        break

                    fpath = os.path.join(dir_path, fname)
                    try:
                        with open(fpath, "r", encoding="utf-8", errors="replace") as fin:
                            text = fin.read().strip()
                    except Exception:
                        continue

                    if len(text) < 50:
                        continue

                    obj = {
                        "text": text,
                        "label": label,
                        "lang": "en",
                        "source": source,
                        "domain": domain,
                    }
                    fout.write(json.dumps(obj, ensure_ascii=False) + "\n")
                    count += 1
                    total += 1
                    if label < 0.3:
                        n_human += 1
                    else:
                        n_ai += 1

                if count > 0:
                    lbl = "human" if label < 0.3 else "AI"
                    print(f"  {gb_dir}: {count} ({lbl})")

        print(f"\n  Итого Ghostbuster: {total} (human={n_human}, ai={n_ai})")
        print(f"  -> {outpath}")

    except subprocess.CalledProcessError as e:
        print(f"  Ошибка git: {e.stderr[:200] if e.stderr else e}")
        print("  Пробую фоллбек через GitHub API...")
        _download_ghostbuster_api(output_dir, outpath, max_per_dir)
    except subprocess.TimeoutExpired:
        print("  Таймаут клонирования. Пробую фоллбек через API...")
        _download_ghostbuster_api(output_dir, outpath, max_per_dir)
    finally:
        shutil.rmtree(tmpdir, ignore_errors=True)

    return outpath


def _download_ghostbuster_api(
    output_dir: str,
    outpath: str,
    max_per_dir: int = 200,
) -> None:
    """Фоллбек: скачиваем через GitHub Contents API (медленнее)."""
    key_dirs = [
        "essay/human", "essay/gpt", "essay/claude",
        "wp/human", "wp/gpt",
        "reuter/human", "reuter/gpt",
        "other/bawe",
    ]

    total = 0
    api_base = "https://api.github.com/repos/vivek3141/ghostbuster-data/contents"

    with open(outpath, "w", encoding="utf-8") as fout:
        for gb_dir in key_dirs:
            label_info = _LABEL_MAP.get(gb_dir)
            if not label_info:
                continue
            label, source, domain = label_info

            url = f"{api_base}/{gb_dir}"
            try:
                req = urllib.request.Request(url)
                req.add_header("User-Agent", "TextHumanize/0.26")
                with urllib.request.urlopen(req, timeout=30) as resp:
                    files = json.loads(resp.read().decode("utf-8"))
            except Exception as e:
                print(f"  API ошибка {gb_dir}: {e}")
                continue

            count = 0
            for finfo in files:
                if count >= max_per_dir:
                    break
                if not finfo.get("name", "").endswith(".txt"):
                    continue

                download_url = finfo.get("download_url", "")
                if not download_url:
                    continue

                try:
                    req = urllib.request.Request(download_url)
                    req.add_header("User-Agent", "TextHumanize/0.26")
                    with urllib.request.urlopen(req, timeout=15) as resp:
                        text = resp.read().decode("utf-8", errors="replace").strip()
                except Exception:
                    continue

                if len(text) < 50:
                    continue

                obj = {
                    "text": text,
                    "label": label,
                    "lang": "en",
                    "source": source,
                    "domain": domain,
                }
                fout.write(json.dumps(obj, ensure_ascii=False) + "\n")
                count += 1
                total += 1

                if count % 30 == 0:
                    time.sleep(1)

            print(f"  {gb_dir}: {count} (API fallback)")

    print(f"\n  Итого (fallback): {total} -> {outpath}")


# ---------------------------------------------------------------------------
# Wikipedia
# ---------------------------------------------------------------------------

def download_wikipedia(
    output_dir: str,
    max_samples: int = 2000,
    langs: list[str] | None = None,
) -> str:
    """Скачать сниппеты из Wikipedia (человеческие тексты)."""
    if langs is None:
        langs = ["en", "ru", "uk", "de", "fr", "es"]

    os.makedirs(output_dir, exist_ok=True)
    outpath = os.path.join(output_dir, "wikipedia_training.jsonl")

    print("=" * 60)
    print("  СКАЧИВАНИЕ WIKIPEDIA СНИППЕТОВ")
    print(f"  Языки: {', '.join(langs)}")
    print(f"  Макс. семплов: {max_samples}")
    print("=" * 60)

    per_lang = max(max_samples // len(langs), 50)
    total = 0

    with open(outpath, "w", encoding="utf-8") as fout:
        for lang in langs:
            api_url = f"https://{lang}.wikipedia.org/api/rest_v1/page/random/summary"
            count = 0
            failures = 0

            while count < per_lang and failures < 30:
                try:
                    req = urllib.request.Request(api_url)
                    req.add_header("User-Agent", "TextHumanize/0.26 (training)")
                    with urllib.request.urlopen(req, timeout=10) as resp:
                        data = json.loads(resp.read().decode("utf-8"))
                except Exception:
                    failures += 1
                    time.sleep(0.5)
                    continue

                extract = data.get("extract", "")
                if len(extract) > 80:
                    obj = {
                        "text": extract.strip(),
                        "label": 0.0,
                        "lang": lang,
                        "source": f"wikipedia_{lang}",
                        "domain": "encyclopedia",
                    }
                    fout.write(json.dumps(obj, ensure_ascii=False) + "\n")
                    count += 1
                    total += 1
                    failures = 0

                if count % 10 == 0:
                    time.sleep(0.3)

            print(f"  Wikipedia/{lang}: {count} сниппетов")

    print(f"\n  Итого Wikipedia: {total} -> {outpath}")
    return outpath


# ---------------------------------------------------------------------------
# Пользовательские JSONL
# ---------------------------------------------------------------------------

def import_user_jsonl(input_path: str, output_dir: str) -> str:
    """Импортировать JSONL данные из файла (JSONL или Markdown с JSONL)."""
    os.makedirs(output_dir, exist_ok=True)
    outpath = os.path.join(output_dir, "user_training.jsonl")

    print("=" * 60)
    print(f"  ИМПОРТ ДАННЫХ: {input_path}")
    print("=" * 60)

    total = 0
    errors = 0

    # Таблица замены «умных» кавычек → обычные (ChatGPT часто выдаёт их)
    _SMART_QUOTES = str.maketrans({
        "\u201c": '"',  # "
        "\u201d": '"',  # "
        "\u2018": "'",  # '
        "\u2019": "'",  # '
        "\u00ab": '"',  # «
        "\u00bb": '"',  # »
    })

    with open(outpath, "w", encoding="utf-8") as fout:
        with open(input_path, "r", encoding="utf-8") as fin:
            for line in fin:
                line = line.strip()
                if not line or not line.startswith(("{", "\u201c")):
                    continue
                # Заменяем умные кавычки
                line = line.translate(_SMART_QUOTES)
                if not line.startswith("{"):
                    continue
                try:
                    obj = json.loads(line)
                    if "text" not in obj or "label" not in obj:
                        continue
                    if len(obj["text"]) < 30:
                        continue
                    obj.setdefault("lang", "en")
                    obj.setdefault("source", "user_generated")
                    obj.setdefault("domain", "mixed")
                    fout.write(json.dumps(obj, ensure_ascii=False) + "\n")
                    total += 1
                except json.JSONDecodeError:
                    errors += 1

    print(f"  Импортировано: {total} семплов, ошибок: {errors}")
    print(f"  -> {outpath}")
    return outpath


# ---------------------------------------------------------------------------
# Объединение и статистика
# ---------------------------------------------------------------------------

def merge_all(output_dir: str, output_name: str = "training_data.jsonl") -> str:
    """Объединить все JSONL файлы в один с дедупликацией."""
    outpath = os.path.join(output_dir, output_name)
    total = 0
    seen: set[int] = set()
    dupes = 0

    print("=" * 60)
    print("  ОБЪЕДИНЕНИЕ ФАЙЛОВ")
    print("=" * 60)

    with open(outpath, "w", encoding="utf-8") as fout:
        for fname in sorted(os.listdir(output_dir)):
            if not fname.endswith(".jsonl") or fname == output_name:
                continue
            fpath = os.path.join(output_dir, fname)
            file_count = 0
            with open(fpath, "r", encoding="utf-8") as fin:
                for line in fin:
                    line = line.strip()
                    if not line:
                        continue
                    try:
                        obj = json.loads(line)
                        h = hash(obj.get("text", "")[:200])
                        if h in seen:
                            dupes += 1
                            continue
                        seen.add(h)
                    except json.JSONDecodeError:
                        continue
                    fout.write(line + "\n")
                    total += 1
                    file_count += 1
            print(f"  {fname}: {file_count} семплов")

    print(f"\n  Объединено: {total} (дубликатов: {dupes})")
    print(f"  -> {outpath}")
    return outpath


def show_stats(path: str) -> None:
    """Показать подробную статистику датасета."""
    n_human = 0
    n_ai = 0
    n_mixed = 0
    langs: dict[str, int] = {}
    sources: dict[str, int] = {}
    domains: dict[str, int] = {}
    text_lens: list[int] = []

    with open(path, "r", encoding="utf-8") as f:
        for line in f:
            try:
                obj = json.loads(line)
            except json.JSONDecodeError:
                continue

            label = obj.get("label", 0.5)
            if label < 0.3:
                n_human += 1
            elif label > 0.7:
                n_ai += 1
            else:
                n_mixed += 1

            lang = obj.get("lang", "?")
            langs[lang] = langs.get(lang, 0) + 1
            src = obj.get("source", "?")
            sources[src] = sources.get(src, 0) + 1
            dom = obj.get("domain", "?")
            domains[dom] = domains.get(dom, 0) + 1
            text_lens.append(len(obj.get("text", "")))

    total = n_human + n_ai + n_mixed
    avg_len = sum(text_lens) / max(len(text_lens), 1)

    print()
    print("=" * 60)
    print(f"  СТАТИСТИКА: {path}")
    print("=" * 60)
    print(f"  Всего:        {total:,}")
    print(f"  Human:        {n_human:,}")
    print(f"  AI:           {n_ai:,}")
    print(f"  Mixed:        {n_mixed:,}")
    print(f"  Баланс H/AI:  {n_human}/{n_ai} = {n_human / max(n_ai, 1):.2f}")
    print(f"  Средняя длина: {avg_len:,.0f} символов")
    print()
    print("  Языки:")
    for lang, cnt in sorted(langs.items(), key=lambda x: -x[1]):
        print(f"    {lang}: {cnt:,}")
    print()
    print("  Источники:")
    for src, cnt in sorted(sources.items(), key=lambda x: -x[1]):
        print(f"    {src}: {cnt:,}")
    print()
    print("  Домены:")
    for dom, cnt in sorted(domains.items(), key=lambda x: -x[1]):
        print(f"    {dom}: {cnt:,}")

    # Уровень
    print()
    if total >= 100_000:
        lvl = "PRODUCTION (100K+) — ~95%"
    elif total >= 50_000:
        lvl = "GREAT (50K+) — ~92%"
    elif total >= 10_000:
        lvl = "GOOD (10K+) — ~85%"
    elif total >= 2_000:
        lvl = "MINIMUM (2K+) — ~75%"
    else:
        lvl = f"МАЛО ({total}) — нужно больше данных"
    print(f"  Уровень: {lvl}")
    print("=" * 60)


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def main() -> None:
    parser = argparse.ArgumentParser(
        description="Скачивание датасетов для обучения AI-детектора",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Примеры:
  python scripts/download_training_data.py                     # Всё
  python scripts/download_training_data.py --dataset hc3       # Только HC3
  python scripts/download_training_data.py --dataset ghostbuster
  python scripts/download_training_data.py --import-file docs/TRAINING_DATA_PROMPT.md
  python scripts/download_training_data.py --merge --stats
        """,
    )
    parser.add_argument("--output", default=OUTPUT_DIR, help="Папка (default: data/)")
    parser.add_argument(
        "--dataset", default="all",
        choices=["hc3", "ghostbuster", "wiki", "all"],
        help="Какой датасет",
    )
    parser.add_argument("--max-hc3", type=int, default=50000, help="Макс. HC3")
    parser.add_argument("--max-ghostbuster", type=int, default=1000, help="Макс. на папку GB")
    parser.add_argument("--max-wiki", type=int, default=2000, help="Макс. Wikipedia")
    parser.add_argument("--wiki-langs", default="en,ru,uk,de,fr,es", help="Языки Wiki")
    parser.add_argument("--import-file", type=str, default="", help="Импорт JSONL")
    parser.add_argument("--merge", action="store_true", help="Объединить файлы")
    parser.add_argument("--stats", action="store_true", help="Показать статистику")
    parser.add_argument("--stats-file", type=str, default="", help="Статистика файла")
    args = parser.parse_args()

    if args.stats_file:
        show_stats(args.stats_file)
        return

    print()
    print("+" + "=" * 58 + "+")
    print("|  TextHumanize — Скачивание данных для обучения           |")
    print("+" + "=" * 58 + "+")
    print()

    downloaded: list[str] = []

    # Импорт пользовательских данных
    if args.import_file:
        path = import_user_jsonl(args.import_file, args.output)
        if path:
            downloaded.append(path)

    # HC3
    if args.dataset in ("hc3", "all"):
        path = download_hc3(args.output, max_samples=args.max_hc3)
        if path:
            downloaded.append(path)

    # Ghostbuster
    if args.dataset in ("ghostbuster", "all"):
        path = download_ghostbuster(args.output, max_per_dir=args.max_ghostbuster)
        if path:
            downloaded.append(path)

    # Wikipedia
    if args.dataset in ("wiki", "all"):
        langs = [l.strip() for l in args.wiki_langs.split(",") if l.strip()]
        path = download_wikipedia(args.output, max_samples=args.max_wiki, langs=langs)
        if path:
            downloaded.append(path)

    # Объединение
    if args.merge or args.dataset == "all":
        merged = merge_all(args.output)
        if args.stats and os.path.isfile(merged):
            show_stats(merged)
    elif args.stats and downloaded:
        for p in downloaded:
            if os.path.isfile(p):
                show_stats(p)

    print()
    print("Для запуска обучения:")
    print("  python -m texthumanize.training_v2 --data data/training_data.jsonl")
    print()


if __name__ == "__main__":
    main()
