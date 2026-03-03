"""CLI-интерфейс TextHumanize — современный визуальный режим с Rich.

Поддерживает graceful fallback на plain-text, если Rich не установлен.
"""

from __future__ import annotations

import argparse
import json
import logging
import sys
import time
from typing import Any

from texthumanize import __version__
from texthumanize.core import (
    adjust_tone,
    analyze,
    analyze_coherence,
    analyze_tone,
    detect_ai,
    detect_watermarks,
    explain,
    full_readability,
    humanize,
    paraphrase,
    spin,
    spin_variants,
)

logger = logging.getLogger(__name__)

# ── Rich availability ─────────────────────────────────────────
_HAS_RICH = False
try:
    from rich import box
    from rich.console import Console
    from rich.panel import Panel
    from rich.progress import (
        BarColumn,
        Progress,
        SpinnerColumn,
        TextColumn,
        TimeElapsedColumn,
    )
    from rich.rule import Rule
    from rich.table import Table
    from rich.text import Text
    from rich.theme import Theme

    _HAS_RICH = True
except ImportError:
    pass

# ── Colour theme ──────────────────────────────────────────────
_TH_THEME = Theme({
    "th.brand": "bold bright_cyan",
    "th.ok": "bold green",
    "th.warn": "bold yellow",
    "th.err": "bold red",
    "th.ai": "bold magenta",
    "th.human": "bold green",
    "th.mixed": "bold yellow",
    "th.dim": "dim",
    "th.key": "bold white",
    "th.val": "cyan",
}) if _HAS_RICH else None  # type: ignore[assignment]

_con = Console(theme=_TH_THEME, stderr=True) if _HAS_RICH else None

# ── All 25 supported languages ───────────────────────────────
_ALL_LANGS = [
    "auto",
    "en", "ru", "uk", "de", "fr", "es", "it", "pl", "pt",
    "nl", "sv", "cs", "ro", "hu", "da",
    "ar", "zh", "ja", "ko", "tr",
    "hi", "vi", "th", "id", "he",
]


# ═══════════════════════════════════════════════════════════════
# BANNER
# ═══════════════════════════════════════════════════════════════

_BANNER = r"""[th.brand]
 ████████╗███████╗██╗  ██╗████████╗
 ╚══██╔══╝██╔════╝╚██╗██╔╝╚══██╔══╝
    ██║   █████╗   ╚███╔╝    ██║
    ██║   ██╔══╝   ██╔██╗    ██║
    ██║   ███████╗██╔╝ ██╗   ██║
    ╚═╝   ╚══════╝╚═╝  ╚═╝   ╚═╝
[/th.brand]   [bold white]TextHumanize[/bold white] [th.dim]v{ver}[/th.dim]  ·  [th.dim]Algorithmic Text Humanization[/th.dim]
"""


def _print_banner() -> None:
    if _HAS_RICH and _con:
        _con.print(_BANNER.format(ver=__version__))
    else:
        print(f"\n{'=' * 50}", file=sys.stderr)
        print(f"  TextHumanize  v{__version__}", file=sys.stderr)
        print("  Algorithmic Text Humanization", file=sys.stderr)
        print(f"{'=' * 50}\n", file=sys.stderr)


# ═══════════════════════════════════════════════════════════════
# HELPERS
# ═══════════════════════════════════════════════════════════════

def _verdict_style(verdict: str) -> tuple[str, str]:
    """Return (icon, rich_style) for a detection verdict."""
    m = {
        "ai": ("\U0001f916", "th.ai"),
        "human": ("\U0001f9d1", "th.human"),
        "mixed": ("\U0001f500", "th.mixed"),
        "unknown": ("\u2753", "th.dim"),
    }
    return m.get(verdict, ("\u2753", "th.dim"))


def _ai_bar(score: float, width: int = 30) -> str:
    """Build a Unicode bar for AI score."""
    filled = int(score * width)
    return "\u2588" * filled + "\u2591" * (width - filled)


def _read_input(path: str) -> str:
    """Read text from a file or stdin."""
    if path == "-":
        return sys.stdin.read()
    try:
        with open(path, encoding="utf-8") as f:
            return f.read()
    except FileNotFoundError:
        msg = f"Error: file '{path}' not found"
        if _con:
            _con.print(f"[th.err]{msg}[/th.err]")
        else:
            print(msg, file=sys.stderr)
        sys.exit(1)
    except Exception as e:
        msg = f"Error reading file: {e}"
        if _con:
            _con.print(f"[th.err]{msg}[/th.err]")
        else:
            print(msg, file=sys.stderr)
        sys.exit(1)


def _output_text(text: str, args: argparse.Namespace) -> None:
    """Write result text to file or stdout."""
    if args.output:
        try:
            with open(args.output, "w", encoding="utf-8") as f:
                f.write(text)
            msg = f"Saved to {args.output}"
            if _con:
                _con.print(f"  [th.ok]\u2714[/th.ok] {msg}")
            else:
                print(msg, file=sys.stderr)
        except Exception as e:
            msg = f"Error writing file: {e}"
            if _con:
                _con.print(f"[th.err]{msg}[/th.err]")
            else:
                print(msg, file=sys.stderr)
            sys.exit(1)
    else:
        print(text)


# ═══════════════════════════════════════════════════════════════
# RICH DISPLAY HELPERS
# ═══════════════════════════════════════════════════════════════

def _display_detection_rich(result: dict, verbose: bool = False) -> None:
    """Show AI detection result with Rich formatting."""
    assert _con is not None
    icon, style = _verdict_style(result["verdict"])

    _con.print()
    header = Text.assemble(("  AI Detection Result  ", "bold white on dark_blue"))
    _con.print(Panel(header, box=box.DOUBLE, border_style="bright_blue", expand=False))

    score = result["score"]
    bar = _ai_bar(score)
    colour = "green" if score < 0.3 else ("yellow" if score < 0.6 else "red")
    _con.print(f"\n  {icon}  Verdict: [{style}]{result['verdict'].upper()}[/{style}]")
    _con.print(f"  \U0001f4ca  AI Score: [{colour}]{score:.1%}[/{colour}]  {bar}")
    _con.print(f"  \U0001f3af  Confidence: {result['confidence']:.1%}")

    if verbose and result.get("metrics"):
        _con.print()
        t = Table(
            title="Detection Metrics",
            box=box.ROUNDED,
            border_style="bright_blue",
            title_style="bold white",
            show_lines=False,
            padding=(0, 1),
        )
        t.add_column("Metric", style="th.key", min_width=25)
        t.add_column("Score", justify="right", style="th.val", min_width=6)
        t.add_column("Bar", min_width=22)

        for metric, val in result["metrics"].items():
            fval = float(val)
            c = "green" if fval < 0.35 else ("yellow" if fval < 0.65 else "red")
            blen = int(fval * 20)
            filled = '\u2588' * blen
            empty = '\u2591' * (20 - blen)
            bar_m = f"[{c}]{filled}{empty}[/{c}]"
            t.add_row(metric, f"{fval:.2f}", bar_m)
        _con.print(t)

    if verbose and result.get("explanations"):
        _con.print()
        _con.print("  [bold]Key findings:[/bold]")
        for exp in result["explanations"]:
            if exp:
                _con.print(f"    \u2022 {exp}")

    _con.print()


def _display_detection_plain(result: dict, verbose: bool = False) -> None:
    """Show AI detection result in plain text."""
    icon_map = {
        "ai": "\U0001f916",
        "human": "\U0001f9d1",
        "mixed": "\U0001f500",
        "unknown": "\u2753",
    }
    icon = icon_map.get(result["verdict"], "")
    print(f"\n  {icon} Verdict: {result['verdict'].upper()}")
    print(f"  AI Probability: {result['score']:.1%}")
    print(f"  Confidence: {result['confidence']:.1%}")

    if verbose:
        print("\n  Metrics (0.0=human, 1.0=AI):")
        for metric, val in result["metrics"].items():
            fval = float(val)
            bar = "\u2588" * int(fval * 20) + "\u2591" * (20 - int(fval * 20))
            print(f"    {metric:25s} {bar} {fval:.2f}")
        if result.get("explanations"):
            print("\n  Key findings:")
            for exp in result["explanations"]:
                if exp:
                    print(f"    \u2022 {exp}")
    print()


def _display_humanize_rich(result: Any, text_before: str, args: argparse.Namespace) -> None:
    """Show humanization result with Rich formatting."""
    assert _con is not None
    _con.print()
    header = Text.assemble(("  Humanization Complete  ", "bold white on dark_green"))
    _con.print(Panel(header, box=box.DOUBLE, border_style="green", expand=False))

    t = Table(box=box.SIMPLE_HEAVY, border_style="green", show_header=False, padding=(0, 2))
    t.add_column("Key", style="th.key")
    t.add_column("Value", style="th.val")
    t.add_row("Language", result.lang)
    t.add_row("Profile", result.profile)
    t.add_row("Intensity", f"{result.intensity}")
    t.add_row("Change ratio", f"{result.change_ratio:.1%}")
    t.add_row("Changes made", f"{len(result.changes)}")
    t.add_row("Chars before", f"{len(text_before):,}")
    t.add_row("Chars after", f"{len(result.text):,}")
    _con.print(t)

    if result.metrics_before and result.metrics_after:
        mt = Table(
            title="Quality Metrics",
            box=box.ROUNDED,
            border_style="bright_blue",
            title_style="bold white",
            show_lines=False,
            padding=(0, 1),
        )
        mt.add_column("Metric", style="th.key", min_width=20)
        mt.add_column("Before", justify="right", min_width=8)
        mt.add_column("After", justify="right", min_width=8)
        mt.add_column("\u0394", justify="right", min_width=8)

        all_keys = set(
            list(result.metrics_before.keys()) + list(result.metrics_after.keys())
        )
        for key in sorted(all_keys):
            before = result.metrics_before.get(key, 0)
            after = result.metrics_after.get(key, 0)
            if isinstance(before, (int, float)) and isinstance(after, (int, float)):
                delta = after - before
                dc = "green" if delta <= 0 else "red"
                if "burstiness" in key or "perplexity" in key or "entropy" in key:
                    dc = "green" if delta >= 0 else "red"
                mt.add_row(
                    key,
                    f"{before:.3f}" if isinstance(before, float) else str(before),
                    f"{after:.3f}" if isinstance(after, float) else str(after),
                    f"[{dc}]{delta:+.3f}[/{dc}]"
                    if isinstance(delta, float)
                    else f"[{dc}]{delta:+d}[/{dc}]",
                )
        _con.print(mt)
    _con.print()


def _display_analyze_rich(report: Any) -> None:
    """Show text analysis with Rich formatting."""
    assert _con is not None
    _con.print()
    header = Text.assemble(("  Text Analysis  ", "bold white on dark_blue"))
    _con.print(Panel(header, box=box.DOUBLE, border_style="bright_blue", expand=False))

    t = Table(box=box.SIMPLE_HEAVY, border_style="bright_blue", show_header=False, padding=(0, 2))
    t.add_column("Key", style="th.key")
    t.add_column("Value", style="th.val")
    t.add_row("Language", report.lang)
    t.add_row("Characters", f"{report.total_chars:,}")
    t.add_row("Words", f"{report.total_words:,}")
    t.add_row("Sentences", f"{report.total_sentences:,}")
    t.add_row("Avg sentence length", f"{report.avg_sentence_length:.1f}")
    t.add_row("Sentence length variance", f"{report.sentence_length_variance:.2f}")
    t.add_row("Bureaucratic ratio", f"{report.bureaucratic_ratio:.4f}")
    t.add_row("Connector ratio", f"{report.connector_ratio:.4f}")
    t.add_row("Repetition score", f"{report.repetition_score:.4f}")
    t.add_row("Typography score", f"{report.typography_score:.4f}")
    art = report.artificiality_score
    ac = "green" if art < 30 else ("yellow" if art < 60 else "red")
    t.add_row("Artificiality", f"[{ac}]{art:.1f}[/{ac}]")
    _con.print(t)

    details = report.details or {}
    if details.get("found_bureaucratic"):
        _con.print("\n  [bold]Found bureaucratic words:[/bold]")
        for w in details["found_bureaucratic"][:15]:
            _con.print(f"    \u2022 [yellow]{w}[/yellow]")
    if details.get("found_connectors"):
        _con.print("\n  [bold]Found AI connectors:[/bold]")
        for w in details["found_connectors"][:15]:
            _con.print(f"    \u2022 [yellow]{w}[/yellow]")
    if details.get("typography_issues"):
        _con.print("\n  [bold]Typography issues:[/bold]")
        for w in details["typography_issues"][:15]:
            _con.print(f"    \u2022 [red]{w}[/red]")
    _con.print()


def _display_tone_rich(result: dict) -> None:
    """Show tone analysis with Rich formatting."""
    assert _con is not None
    _con.print()
    header = Text.assemble(("  Tone Analysis  ", "bold white on rgb(100,50,150)"))
    _con.print(Panel(header, box=box.DOUBLE, border_style="magenta", expand=False))

    t = Table(box=box.ROUNDED, border_style="magenta", show_header=True, padding=(0, 1))
    t.add_column("Tone", style="th.key", min_width=15)
    t.add_column("Score", justify="right", style="th.val", min_width=8)
    t.add_column("Bar", min_width=22)

    for tone, score in sorted(
        result.items(),
        key=lambda x: -x[1] if isinstance(x[1], (int, float)) else 0,
    ):
        if isinstance(score, (int, float)):
            sc = float(score)
            c = "bright_cyan" if sc > 0.3 else "white"
            blen = int(sc * 20)
            filled = '\u2588' * blen
            empty = '\u2591' * (20 - blen)
            bar_t = f"[{c}]{filled}{empty}[/{c}]"
            t.add_row(tone, f"{sc:.2f}", bar_t)
    _con.print(t)
    _con.print()


def _display_coherence_rich(result: dict) -> None:
    """Show coherence analysis with Rich formatting."""
    assert _con is not None
    _con.print()
    header = Text.assemble(("  Coherence Analysis  ", "bold white on dark_green"))
    _con.print(Panel(header, box=box.DOUBLE, border_style="green", expand=False))

    t = Table(box=box.SIMPLE_HEAVY, border_style="green", show_header=False, padding=(0, 2))
    t.add_column("Key", style="th.key")
    t.add_column("Value", style="th.val")
    for k, v in result.items():
        if isinstance(v, float):
            t.add_row(k, f"{v:.3f}")
        elif isinstance(v, (list, dict)):
            t.add_row(k, json.dumps(v, ensure_ascii=False)[:80])
        else:
            t.add_row(k, str(v))
    _con.print(t)
    _con.print()


def _display_readability_rich(result: dict) -> None:
    """Show readability analysis with Rich formatting."""
    assert _con is not None
    _con.print()
    header = Text.assemble(("  Readability Analysis  ", "bold white on dark_blue"))
    _con.print(Panel(header, box=box.DOUBLE, border_style="bright_blue", expand=False))

    t = Table(
        box=box.ROUNDED,
        border_style="bright_blue",
        title_style="bold white",
        show_lines=False,
        padding=(0, 1),
    )
    t.add_column("Metric", style="th.key", min_width=25)
    t.add_column("Value", justify="right", style="th.val", min_width=10)

    for k, v in result.items():
        if isinstance(v, float):
            t.add_row(k, f"{v:.2f}")
        elif isinstance(v, dict):
            for sub_k, sub_v in v.items():
                t.add_row(
                    f"  {sub_k}",
                    f"{sub_v:.2f}" if isinstance(sub_v, float) else str(sub_v),
                )
        else:
            t.add_row(k, str(v))
    _con.print(t)
    _con.print()


# ═══════════════════════════════════════════════════════════════
# BENCHMARK
# ═══════════════════════════════════════════════════════════════

def _get_benchmark_samples(lang: str) -> list[tuple[str, str]]:
    """Return list of (label, text) benchmark samples for *lang*."""
    _en_short = (
        "Furthermore, it is important to note that the implementation "
        "of this approach facilitates optimization."
    )
    _en_medium = (
        "Furthermore, it is important to note that the implementation of cloud computing facilitates the "
        "optimization of business processes. Additionally, the utilization of microservices constitutes a significant "
        "advancement. Nevertheless, considerable challenges remain in the area of security. It is worth mentioning "
        "that these challenges necessitate comprehensive solutions. Moreover, the integration of artificial "
        "intelligence provides unprecedented opportunities for automation."
    )
    _ru_short = (
        "Необходимо отметить, что данный подход является оптимальным "
        "решением для осуществления поставленных задач."
    )
    _ru_medium = (
        "Необходимо отметить, что данный подход является оптимальным решением для осуществления поставленных задач. "
        "Кроме того, следует подчеркнуть важность реализации инновационных методологий. В рамках данного исследования "
        "было установлено, что применение современных технологий способствует повышению эффективности. Тем не менее, "
        "существуют определённые ограничения, которые необходимо учитывать."
    )
    _uk_short = (
        "Необхідно зазначити, що даний підхід є фундаментальним "
        "для здійснення оптимізації процесів."
    )
    _uk_medium = (
        "Необхідно зазначити, що даний підхід є фундаментальним для здійснення оптимізації процесів. "
        "Крім того, варто підкреслити, що реалізація інноваційних методологій забезпечує всебічне покращення "
        "ефективності. Таким чином, систематичне впровадження відповідних заходів сприяє досягненню стратегічних цілей."
    )

    m: dict[str, list[tuple[str, str]]] = {
        "en": [
            ("short", _en_short),
            ("medium", _en_medium),
            ("long", (_en_medium + " ") * 3),
        ],
        "ru": [
            ("short", _ru_short),
            ("medium", _ru_medium),
            ("long", (_ru_medium + " ") * 3),
        ],
        "uk": [
            ("short", _uk_short),
            ("medium", _uk_medium),
            ("long", (_uk_medium + " ") * 3),
        ],
    }
    return m.get(lang, m["en"])


def _handle_benchmark_rich(args: argparse.Namespace, remaining: list[str]) -> None:
    """Run benchmark with Rich progress bars."""
    assert _con is not None
    lang = args.lang if hasattr(args, "lang") and args.lang != "auto" else "en"

    _print_banner()
    _con.print(Rule("[bold]Benchmark Suite[/bold]", style="bright_blue"))
    _con.print(f"  Language: [th.val]{lang}[/th.val]\n")

    samples = _get_benchmark_samples(lang)
    total_chars = 0
    total_time_h = 0.0
    quality_scores: list[float] = []
    change_ratios: list[float] = []
    ai_improvements: list[tuple[float, float]] = []

    res_table = Table(
        title="Benchmark Results",
        box=box.ROUNDED,
        border_style="bright_blue",
        title_style="bold white",
        show_lines=True,
        padding=(0, 1),
    )
    res_table.add_column("Sample", style="th.key")
    res_table.add_column("Chars", justify="right")
    res_table.add_column("Humanize", justify="right")
    res_table.add_column("Throughput", justify="right")
    res_table.add_column("Change%", justify="right")
    res_table.add_column("AI Before", justify="right")
    res_table.add_column("AI After", justify="right")

    with Progress(
        SpinnerColumn("dots"),
        TextColumn("[progress.description]{task.description}"),
        BarColumn(bar_width=20),
        TextColumn("[progress.percentage]{task.percentage:>3.0f}%"),
        TimeElapsedColumn(),
        console=_con,
    ) as progress:
        task = progress.add_task("Running benchmark...", total=len(samples))
        for label, sample_text in samples:
            chars = len(sample_text)
            total_chars += chars

            t0 = time.perf_counter()
            result = humanize(sample_text, lang=lang, profile="web", intensity=60, seed=42)
            t_h = time.perf_counter() - t0
            total_time_h += t_h

            ai_before = detect_ai(sample_text, lang=lang)
            ai_after = detect_ai(result.text, lang=lang)

            quality_scores.append(getattr(result, "quality_score", 0.0))
            change_ratios.append(getattr(result, "change_ratio", 0.0))
            ai_improvements.append((ai_before["score"], ai_after["score"]))

            throughput = round(chars / t_h) if t_h > 0 else 0
            sc_b, sc_a = ai_before["score"], ai_after["score"]
            c_b = "red" if sc_b > 0.5 else "yellow"
            c_a = "green" if sc_a < 0.3 else ("yellow" if sc_a < 0.6 else "red")
            res_table.add_row(
                label,
                f"{chars:,}",
                f"{t_h * 1000:.0f}ms",
                f"{throughput:,} c/s",
                f"{getattr(result, 'change_ratio', 0):.1%}",
                f"[{c_b}]{sc_b:.0%}[/{c_b}]",
                f"[{c_a}]{sc_a:.0%}[/{c_a}]",
            )
            progress.advance(task)

    _con.print(res_table)

    # Determinism test
    r1 = humanize(samples[0][1], lang=lang, seed=12345)
    r2 = humanize(samples[0][1], lang=lang, seed=12345)
    deterministic = r1.text == r2.text

    avg_throughput = round(total_chars / total_time_h) if total_time_h > 0 else 0
    avg_quality = (
        round(sum(quality_scores) / len(quality_scores), 3) if quality_scores else 0
    )
    avg_change = (
        round(sum(change_ratios) / len(change_ratios), 3) if change_ratios else 0
    )
    avg_ai_drop = (
        round(
            sum(b - a for b, a in ai_improvements) / len(ai_improvements), 3
        )
        if ai_improvements
        else 0
    )

    _con.print()
    _con.print(Rule("[bold]Summary[/bold]", style="green"))

    st = Table(box=box.SIMPLE_HEAVY, border_style="green", show_header=False, padding=(0, 2))
    st.add_column("Key", style="th.key")
    st.add_column("Value", style="th.val")
    st.add_row("Total chars", f"{total_chars:,}")
    st.add_row("Avg throughput", f"{avg_throughput:,} chars/sec")
    st.add_row("Avg quality", f"{avg_quality:.2f}")
    st.add_row("Avg change ratio", f"{avg_change:.1%}")
    dc = "green" if avg_ai_drop > 0 else "red"
    st.add_row("Avg AI score drop", f"[{dc}]{avg_ai_drop:+.1%}[/{dc}]")
    st.add_row("Deterministic", "\u2705" if deterministic else "\u274c")
    _con.print(st)
    _con.print()


def _handle_benchmark_plain(args: argparse.Namespace, remaining: list[str]) -> None:
    """Run benchmark in plain text mode."""
    use_json = getattr(args, 'json', False) or "--json" in remaining
    lang = args.lang if hasattr(args, "lang") and args.lang != "auto" else "en"
    samples = _get_benchmark_samples(lang)

    total_chars = 0
    total_time_h = 0.0
    total_time_d = 0.0
    quality_scores: list[float] = []
    change_ratios: list[float] = []
    ai_improvements: list[tuple[float, float]] = []
    results_data: list[dict] = []

    if not use_json:
        print("=" * 60)
        print(f"  TextHumanize Benchmark \u2014 v{__version__}")
        print(f"  Language: {lang}")
        print("=" * 60)

    for label, sample_text in samples:
        chars = len(sample_text)
        total_chars += chars

        t0 = time.perf_counter()
        result = humanize(sample_text, lang=lang, profile="web", intensity=60, seed=42)
        t_h = time.perf_counter() - t0
        total_time_h += t_h

        t0 = time.perf_counter()
        ai_before = detect_ai(sample_text, lang=lang)
        t_d = time.perf_counter() - t0
        total_time_d += t_d

        ai_after = detect_ai(result.text, lang=lang)
        quality_scores.append(getattr(result, "quality_score", 0.0))
        change_ratios.append(getattr(result, "change_ratio", 0.0))
        ai_improvements.append((ai_before["score"], ai_after["score"]))

        row = {
            "label": label,
            "chars": chars,
            "humanize_ms": round(t_h * 1000, 1),
            "detect_ms": round(t_d * 1000, 1),
            "throughput": round(chars / t_h) if t_h > 0 else 0,
            "change_ratio": round(getattr(result, "change_ratio", 0), 3),
            "quality_score": round(getattr(result, "quality_score", 0), 3),
            "ai_before": round(ai_before["score"], 3),
            "ai_after": round(ai_after["score"], 3),
            "verdict_before": ai_before["verdict"],
            "verdict_after": ai_after["verdict"],
        }
        results_data.append(row)

        if not use_json:
            print(f"\n  [{label}] {chars} chars")
            print(f"    Humanize: {row['humanize_ms']}ms ({row['throughput']:,} chars/sec)")
            print(f"    Detect:   {row['detect_ms']}ms")
            print(f"    Change:   {row['change_ratio']:.1%}")
            print(
                f"    AI score: {row['ai_before']:.0%} \u2192 {row['ai_after']:.0%} "
                f"({row['verdict_before']} \u2192 {row['verdict_after']})"
            )

    # Determinism
    r1 = humanize(samples[0][1], lang=lang, seed=12345)
    r2 = humanize(samples[0][1], lang=lang, seed=12345)
    deterministic = r1.text == r2.text

    avg_throughput = round(total_chars / total_time_h) if total_time_h > 0 else 0
    avg_quality = (
        round(sum(quality_scores) / len(quality_scores), 3) if quality_scores else 0
    )
    avg_change = (
        round(sum(change_ratios) / len(change_ratios), 3) if change_ratios else 0
    )
    avg_ai_drop = (
        round(sum(b - a for b, a in ai_improvements) / len(ai_improvements), 3)
        if ai_improvements
        else 0
    )

    summary = {
        "version": __version__,
        "lang": lang,
        "total_chars": total_chars,
        "total_humanize_ms": round(total_time_h * 1000, 1),
        "total_detect_ms": round(total_time_d * 1000, 1),
        "avg_throughput_chars_sec": avg_throughput,
        "avg_quality_score": avg_quality,
        "avg_change_ratio": avg_change,
        "avg_ai_score_drop": avg_ai_drop,
        "deterministic": deterministic,
        "samples": results_data,
    }

    if use_json:
        print(json.dumps(summary, ensure_ascii=False, indent=2))
    else:
        print(f"\n{'=' * 60}")
        print("  SUMMARY")
        print(f"{'=' * 60}")
        print(f"  Total chars:    {total_chars:,}")
        print(f"  Avg throughput: {avg_throughput:,} chars/sec")
        print(f"  Avg quality:    {avg_quality:.2f}")
        print(f"  Avg change:     {avg_change:.1%}")
        print(f"  Avg AI drop:    {avg_ai_drop:+.1%}")
        det_icon = "\u2705" if deterministic else "\u274c"
        print(f"  Deterministic:  {det_icon}")
        print("=" * 60)


# ═══════════════════════════════════════════════════════════════
# TRAINING
# ═══════════════════════════════════════════════════════════════

def _handle_train_command(args: argparse.Namespace, remaining: list[str]) -> None:
    """Handle 'train' subcommand."""
    n_samples = 500
    epochs = 20
    lm_epochs = 3
    output_dir = "texthumanize/weights"
    use_json = getattr(args, 'json', False)
    verbose = True

    i = 0
    while i < len(remaining):
        a = remaining[i]
        if a in ("--samples", "-n") and i + 1 < len(remaining):
            n_samples = int(remaining[i + 1])
            i += 2
        elif a in ("--epochs", "-e") and i + 1 < len(remaining):
            epochs = int(remaining[i + 1])
            i += 2
        elif a == "--lm-epochs" and i + 1 < len(remaining):
            lm_epochs = int(remaining[i + 1])
            i += 2
        elif a in ("--output", "-o") and i + 1 < len(remaining):
            output_dir = remaining[i + 1]
            i += 2
        elif a == "--json":
            use_json = True
            i += 1
        elif a == "--quiet":
            verbose = False
            i += 1
        else:
            i += 1

    from texthumanize.training import Trainer

    t0 = time.time()
    trainer = Trainer(seed=42)

    if _HAS_RICH and _con and not use_json:
        _print_banner()
        _con.print(Rule("[bold]Neural Training[/bold]", style="bright_cyan"))
        _con.print()

        with Progress(
            SpinnerColumn("dots"),
            TextColumn("[progress.description]{task.description}"),
            BarColumn(bar_width=30),
            TextColumn("[progress.percentage]{task.percentage:>3.0f}%"),
            TimeElapsedColumn(),
            console=_con,
        ) as progress:
            task1 = progress.add_task(
                f"[1/4] Generating {n_samples} samples...", total=1
            )
            data_stats = trainer.generate_data(n_samples=n_samples)
            progress.update(
                task1,
                completed=1,
                description=f"[1/4] Generated: train={data_stats['train']}, val={data_stats['val']}",
            )

            task2 = progress.add_task(
                f"[2/4] Training MLP ({epochs} epochs)...", total=epochs
            )
            result_d = trainer.train_detector(epochs=epochs, verbose=False)
            progress.update(
                task2,
                completed=epochs,
                description=f"[2/4] MLP done \u2014 acc={result_d['best_val_accuracy']:.1%}",
            )

            task3 = progress.add_task("[3/4] Exporting weights...", total=1)
            trainer.export_weights(output_dir)
            progress.update(task3, completed=1)

            lm_result = None
            if lm_epochs > 0:
                task4 = progress.add_task(
                    f"[4/4] Training LSTM LM ({lm_epochs} epochs)...",
                    total=lm_epochs,
                )
                lm_result = trainer.train_lm(epochs=lm_epochs, verbose=False)
                trainer.export_lm_weights(lm_result, output_dir)
                progress.update(task4, completed=lm_epochs)

        elapsed = time.time() - t0
        _con.print()
        st = Table(box=box.SIMPLE_HEAVY, border_style="green", show_header=False, padding=(0, 2))
        st.add_column("Key", style="th.key")
        st.add_column("Value", style="th.val")
        m = result_d["final_metrics"]
        st.add_row("Best accuracy", f"{result_d['best_val_accuracy']:.1%}")
        st.add_row("F1 score", f"{m['f1']:.2f}")
        st.add_row("Parameters", f"{result_d['param_count']:,}")
        if lm_result:
            st.add_row(
                "LM final loss",
                f"{lm_result['training_log'][-1]['avg_loss']:.4f}",
            )
        st.add_row("Elapsed", f"{elapsed:.1f}s")
        st.add_row("Output", output_dir)
        _con.print(st)
        _con.print()
    else:
        if not use_json and verbose:
            print("=" * 50)
            print("  TextHumanize Neural Training")
            print("=" * 50)

        if verbose and not use_json:
            print(f"\n[1/4] Generating {n_samples} training samples...")
        data_stats = trainer.generate_data(n_samples=n_samples)
        if verbose and not use_json:
            print(f"  Train: {data_stats['train']}, Val: {data_stats['val']}")

        if verbose and not use_json:
            print(f"\n[2/4] Training MLP detector ({epochs} epochs)...")
        result_d = trainer.train_detector(epochs=epochs, verbose=verbose)
        if verbose and not use_json:
            mm = result_d["final_metrics"]
            print(f"  Best accuracy: {result_d['best_val_accuracy']:.1%}")
            print(f"  F1={mm['f1']:.2f}")

        if verbose and not use_json:
            print("\n[3/4] Exporting weights...")
        trainer.export_weights(output_dir)

        lm_result = None
        if lm_epochs > 0:
            if verbose and not use_json:
                print(f"\n[4/4] Training LSTM LM ({lm_epochs} epochs)...")
            lm_result = trainer.train_lm(epochs=lm_epochs, verbose=verbose)
            trainer.export_lm_weights(lm_result, output_dir)

        elapsed = time.time() - t0
        if use_json:
            summary = {
                "training_samples": data_stats,
                "detector": {
                    "epochs": result_d["epochs_trained"],
                    "best_accuracy": result_d["best_val_accuracy"],
                    "final_metrics": result_d["final_metrics"],
                    "param_count": result_d["param_count"],
                },
                "lm": {
                    "epochs": lm_result["epochs_trained"],
                    "final_loss": lm_result["training_log"][-1]["avg_loss"],
                }
                if lm_result
                else None,
                "output_dir": output_dir,
                "elapsed_seconds": round(elapsed, 1),
            }
            print(json.dumps(summary, ensure_ascii=False, indent=2, default=str))
        elif verbose:
            print(f"\n{'=' * 50}")
            print(f"  Training complete in {elapsed:.1f}s")
            print(f"  Weights saved to: {output_dir}/")
            print(f"{'=' * 50}")


# ═══════════════════════════════════════════════════════════════
# DETECT SUBCOMMAND
# ═══════════════════════════════════════════════════════════════

def _handle_detect_command(args: argparse.Namespace, remaining: list[str]) -> None:
    """Handle 'detect' subcommand."""
    detect_input = "-"
    use_json = getattr(args, 'json', False)
    verbose = getattr(args, "verbose", False)

    for a in remaining:
        if a == "--json":
            use_json = True
        elif a == "--verbose":
            verbose = True
        elif not a.startswith("-"):
            detect_input = a

    text = _read_input(detect_input)
    lang = args.lang if hasattr(args, "lang") else "auto"

    if _HAS_RICH and _con and not use_json:
        _print_banner()
        with _con.status(
            "[bold bright_cyan]Analyzing text...[/bold bright_cyan]", spinner="dots"
        ):
            result = detect_ai(text, lang=lang)
        _display_detection_rich(result, verbose=verbose)
    else:
        result = detect_ai(text, lang=lang)
        if use_json:
            print(json.dumps(result, ensure_ascii=False, indent=2))
        else:
            _display_detection_plain(result, verbose=verbose)


# ═══════════════════════════════════════════════════════════════
# MAIN
# ═══════════════════════════════════════════════════════════════

def main() -> None:
    """Entry point for CLI."""
    parser = argparse.ArgumentParser(
        prog="texthumanize",
        description=(
            "TextHumanize \u2014 Algorithmic Text Humanization. "
            "Makes AI-generated text natural."
        ),
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  texthumanize input.txt
  texthumanize input.txt -l uk -p chat -i 80
  texthumanize input.txt -o output.txt --report report.json
  texthumanize input.txt --keep "Brand" "Term"
  texthumanize --analyze input.txt
  texthumanize detect input.txt
  texthumanize detect input.txt --verbose
  texthumanize train --samples 1000 --epochs 30
  texthumanize benchmark --lang en
  echo "Text" | texthumanize detect -
  echo "Text" | texthumanize -
        """,
    )

    parser.add_argument(
        "input",
        help="Input file ('-' for stdin), or subcommand: detect, train, benchmark",
    )
    parser.add_argument("-o", "--output", help="Output file (default: stdout)")
    parser.add_argument(
        "-l",
        "--lang",
        default="auto",
        choices=_ALL_LANGS,
        help="Text language (default: auto)",
    )
    parser.add_argument(
        "-p",
        "--profile",
        default="web",
        choices=[
            "chat", "web", "seo", "docs", "formal",
            "academic", "marketing", "social", "email",
        ],
        help="Processing profile (default: web)",
    )
    parser.add_argument(
        "-i",
        "--intensity",
        type=int,
        default=60,
        help="Processing intensity 0-100 (default: 60)",
    )
    parser.add_argument(
        "--keep", nargs="*", default=[], help="Keywords to preserve"
    )
    parser.add_argument(
        "--brand", nargs="*", default=[], help="Brand terms to protect"
    )
    parser.add_argument(
        "--max-change",
        type=float,
        default=0.4,
        help="Max change ratio 0-1 (default: 0.4)",
    )
    parser.add_argument("--report", help="Save JSON report to file")
    parser.add_argument(
        "--analyze", action="store_true", help="Analysis only (no processing)"
    )
    parser.add_argument(
        "--explain", action="store_true", help="Show detailed change report"
    )
    parser.add_argument("--detect-ai", action="store_true", help="AI detection mode")
    parser.add_argument("--verbose", action="store_true", help="Verbose output")
    parser.add_argument("--paraphrase", action="store_true", help="Paraphrase text")
    parser.add_argument(
        "--tone",
        metavar="TARGET",
        help="Adjust tone (neutral, formal, casual, academic, marketing)",
    )
    parser.add_argument("--tone-analyze", action="store_true", help="Tone analysis")
    parser.add_argument(
        "--watermarks", action="store_true", help="Detect and remove watermarks"
    )
    parser.add_argument("--spin", action="store_true", help="Text spinning")
    parser.add_argument(
        "--variants", type=int, metavar="N", help="Generate N spin variants"
    )
    parser.add_argument("--coherence", action="store_true", help="Coherence analysis")
    parser.add_argument(
        "--readability", action="store_true", help="Full readability analysis"
    )
    parser.add_argument("--grammar", action="store_true", help="Grammar check")
    parser.add_argument("--grammar-fix", action="store_true", help="Auto-fix grammar")
    parser.add_argument("--health", action="store_true", help="Content health score")
    parser.add_argument("--uniqueness", action="store_true", help="Uniqueness score")
    parser.add_argument("--api", action="store_true", help="Start API server")
    parser.add_argument(
        "--port", type=int, default=8080, help="API server port (default: 8080)"
    )
    parser.add_argument("--seed", type=int, help="Seed for reproducibility")
    parser.add_argument(
        "--json", action="store_true", help="JSON output for all commands"
    )
    parser.add_argument(
        "--no-color", action="store_true", help="Disable rich formatting"
    )
    parser.add_argument(
        "-v", "--version", action="version", version=f"texthumanize {__version__}"
    )

    args, remaining = parser.parse_known_args()

    # ── Disable Rich if --no-color ──
    global _HAS_RICH, _con
    if args.no_color:
        _HAS_RICH = False
        _con = None

    # ── Subcommands ──
    if args.input == "detect":
        _handle_detect_command(args, remaining)
        return
    if args.input == "train":
        _handle_train_command(args, remaining)
        return
    if args.input == "benchmark":
        if _HAS_RICH and _con and not getattr(args, 'json', False):
            _handle_benchmark_rich(args, remaining)
        else:
            _handle_benchmark_plain(args, remaining)
        return

    # ── API server ──
    if getattr(args, "api", False):
        from texthumanize.api import run_server

        run_server(port=args.port)
        return

    # ── Read input ──
    text = _read_input(args.input)
    use_json_flag = getattr(args, "json", False)

    # ── AI Detection ──
    if getattr(args, "detect_ai", False):
        if _HAS_RICH and _con and not use_json_flag:
            _print_banner()
            with _con.status(
                "[bold bright_cyan]Analyzing text...[/bold bright_cyan]",
                spinner="dots",
            ):
                result_d = detect_ai(text, lang=args.lang)
            _display_detection_rich(result_d, verbose=args.verbose)
        else:
            result_d = detect_ai(text, lang=args.lang)
        print(json.dumps(result_d, ensure_ascii=False, indent=2))
        return

    # ── Paraphrase ──
    if getattr(args, "paraphrase", False):
        if _HAS_RICH and _con and not use_json_flag:
            _print_banner()
            with _con.status(
                "[bold bright_cyan]Paraphrasing...[/bold bright_cyan]",
                spinner="dots",
            ):
                result_text = paraphrase(
                    text, lang=args.lang, intensity=args.intensity / 100.0
                )
            _con.print(
                Panel(
                    Text.assemble(
                        ("  Paraphrase Complete  ", "bold white on dark_green")
                    ),
                    box=box.DOUBLE,
                    border_style="green",
                    expand=False,
                )
            )
        else:
            result_text = paraphrase(
                text, lang=args.lang, intensity=args.intensity / 100.0
            )
        _output_text(result_text, args)
        return

    # ── Tone analysis ──
    if getattr(args, "tone_analyze", False):
        result_tone = analyze_tone(text, lang=args.lang)
        if _HAS_RICH and _con and not use_json_flag:
            _print_banner()
            _display_tone_rich(result_tone)
        print(json.dumps(result_tone, ensure_ascii=False, indent=2))
        return

    # ── Tone adjustment ──
    if getattr(args, "tone", None):
        if _HAS_RICH and _con and not use_json_flag:
            _print_banner()
            with _con.status(
                f"[bold bright_cyan]Adjusting tone to {args.tone}...[/bold bright_cyan]",
                spinner="dots",
            ):
                result_text = adjust_tone(text, target=args.tone, lang=args.lang)
            _con.print(
                Panel(
                    Text.assemble(
                        ("  Tone Adjusted  ", "bold white on dark_green")
                    ),
                    box=box.DOUBLE,
                    border_style="green",
                    expand=False,
                )
            )
        else:
            result_text = adjust_tone(text, target=args.tone, lang=args.lang)
        _output_text(result_text, args)
        return

    # ── Watermarks ──
    if getattr(args, "watermarks", False):
        result_wm = detect_watermarks(text, lang=args.lang)
        if result_wm["has_watermarks"]:
            if _con:
                _con.print("[th.warn]  \u26a0  Водяные знаки обнаружены![/th.warn]")
            else:
                print("Водяные знаки обнаружены.", file=sys.stderr)
            _output_text(result_wm["cleaned_text"], args)
        else:
            if _con:
                _con.print("[th.ok]  \u2714  Водяные знаки не обнаружены.[/th.ok]")
            else:
                print("Водяные знаки не обнаружены.", file=sys.stderr)
            _output_text(text, args)
        return

    # ── Spin ──
    if getattr(args, "spin", False):
        if _HAS_RICH and _con and not use_json_flag:
            _print_banner()
            with _con.status(
                "[bold bright_cyan]Spinning text...[/bold bright_cyan]",
                spinner="dots",
            ):
                result_text = spin(
                    text, lang=args.lang, intensity=args.intensity / 100.0
                )
            _con.print(
                Panel(
                    Text.assemble(
                        ("  Spin Complete  ", "bold white on dark_green")
                    ),
                    box=box.DOUBLE,
                    border_style="green",
                    expand=False,
                )
            )
        else:
            result_text = spin(
                text, lang=args.lang, intensity=args.intensity / 100.0
            )
        _output_text(result_text, args)
        return

    # ── Spin variants ──
    if getattr(args, "variants", None):
        results_v = spin_variants(text, count=args.variants, lang=args.lang)
        if _HAS_RICH and _con and not use_json_flag:
            _print_banner()
            for idx, v in enumerate(results_v, 1):
                _con.print(Rule(f"\u0412\u0430\u0440\u0438\u0430\u043d\u0442 {idx}", style="bright_cyan"))
                _con.print(v)
                _con.print()
        for idx, v in enumerate(results_v, 1):
            print(f"--- \u0412\u0430\u0440\u0438\u0430\u043d\u0442 {idx} ---")
            print(v)
            print()
        return

    # ── Coherence ──
    if getattr(args, "coherence", False):
        result_c = analyze_coherence(text, lang=args.lang)
        if _HAS_RICH and _con and not use_json_flag:
            _print_banner()
            _display_coherence_rich(result_c)
        print(json.dumps(result_c, ensure_ascii=False, indent=2))
        return

    # ── Readability ──
    if getattr(args, "readability", False):
        result_r = full_readability(text, lang=args.lang)
        if _HAS_RICH and _con and not use_json_flag:
            _print_banner()
            _display_readability_rich(result_r)
        print(json.dumps(result_r, ensure_ascii=False, indent=2))
        return

    # ── Grammar check ──
    if getattr(args, "grammar", False):
        from texthumanize.grammar import check_grammar

        gram_result = check_grammar(text, lang=args.lang)
        if _HAS_RICH and _con and not use_json_flag:
            _print_banner()
            _con.print(
                Panel(
                    Text.assemble(
                        ("  Grammar Check  ", "bold white on dark_blue")
                    ),
                    box=box.DOUBLE,
                    border_style="bright_blue",
                    expand=False,
                )
            )
            if gram_result.issues:
                gt = Table(
                    box=box.ROUNDED,
                    border_style="yellow",
                    show_lines=True,
                    padding=(0, 1),
                )
                gt.add_column("#", style="dim", width=3)
                gt.add_column("Issue", style="th.key")
                gt.add_column("Suggestion", style="th.val")
                gt.add_column("Context", style="dim")
                for gi, issue in enumerate(gram_result.issues[:20], 1):
                    gt.add_row(
                        str(gi),
                        str(issue.message),
                        str(issue.suggestion) if issue.suggestion else "-",
                        str(issue.context)[:60] if issue.context else "-",
                    )
                _con.print(gt)
            else:
                _con.print("[th.ok]  \u2714  No grammar issues found.[/th.ok]")
        else:
            output_g = {
                "issues_count": len(gram_result.issues),
                "issues": [
                    {"message": i.message, "suggestion": i.suggestion}
                    for i in gram_result.issues
                ],
            }
            print(json.dumps(output_g, ensure_ascii=False, indent=2))
        return

    # ── Grammar fix ──
    if getattr(args, "grammar_fix", False):
        from texthumanize.grammar import fix_grammar

        fixed_text = fix_grammar(text, lang=args.lang)
        if _HAS_RICH and _con and not use_json_flag:
            _print_banner()
            _con.print(
                Panel(
                    Text.assemble(
                        ("  Grammar Fixed  ", "bold white on dark_green")
                    ),
                    box=box.DOUBLE,
                    border_style="green",
                    expand=False,
                )
            )
        _output_text(fixed_text, args)
        return

    # ── Content health ──
    if getattr(args, "health", False):
        from texthumanize.health_score import content_health

        health_r = content_health(text, lang=args.lang)
        if _HAS_RICH and _con and not use_json_flag:
            _print_banner()
            _con.print(
                Panel(
                    Text.assemble(
                        ("  Content Health  ", "bold white on dark_green")
                    ),
                    box=box.DOUBLE,
                    border_style="green",
                    expand=False,
                )
            )
            ht = Table(
                box=box.SIMPLE_HEAVY,
                border_style="green",
                show_header=False,
                padding=(0, 2),
            )
            ht.add_column("Key", style="th.key")
            ht.add_column("Value", style="th.val")
            ht.add_row("Overall score", f"{health_r.score:.1f}/100")
            ht.add_row("Grade", health_r.grade)
            for comp in health_r.components:
                sc = comp.score
                c = "green" if sc >= 70 else ("yellow" if sc >= 40 else "red")
                ht.add_row(comp.name, f"[{c}]{sc:.0f}[/{c}]")
            _con.print(ht)
        else:
            print(
                json.dumps(
                    {
                        "score": health_r.score,
                        "grade": health_r.grade,
                        "components": [
                            {"name": c.name, "score": c.score}
                            for c in health_r.components
                        ],
                    },
                    ensure_ascii=False,
                    indent=2,
                )
            )
        return

    # ── Uniqueness ──
    if getattr(args, "uniqueness", False):
        from texthumanize.uniqueness import uniqueness_score

        uniq = uniqueness_score(text, lang=args.lang)
        if _HAS_RICH and _con and not use_json_flag:
            _print_banner()
            sc = uniq.score
            c = "green" if sc >= 0.7 else ("yellow" if sc >= 0.4 else "red")
            _con.print(f"\n  \U0001f4ca  Uniqueness: [{c}]{sc:.1%}[/{c}]")
            _con.print(f"  \U0001f4dd  Fingerprint type: {uniq.method}\n")
        else:
            print(
                json.dumps(
                    {"score": uniq.score, "method": uniq.method},
                    ensure_ascii=False,
                    indent=2,
                )
            )
        return

    # ── Analysis ──
    if args.analyze:
        report = analyze(text, lang=args.lang)
        if _HAS_RICH and _con and not use_json_flag:
            _print_banner()
            _display_analyze_rich(report)
        output_a = {
            "lang": report.lang,
            "total_chars": report.total_chars,
            "total_words": report.total_words,
            "total_sentences": report.total_sentences,
            "avg_sentence_length": round(report.avg_sentence_length, 2),
            "sentence_length_variance": round(
                report.sentence_length_variance, 2
            ),
            "bureaucratic_ratio": round(report.bureaucratic_ratio, 4),
            "connector_ratio": round(report.connector_ratio, 4),
            "repetition_score": round(report.repetition_score, 4),
            "typography_score": round(report.typography_score, 4),
            "artificiality_score": round(report.artificiality_score, 2),
            "details": {
                "found_bureaucratic": report.details.get(
                    "found_bureaucratic", []
                ),
                "found_connectors": report.details.get(
                    "found_connectors", []
                ),
                "typography_issues": report.details.get(
                    "typography_issues", []
                ),
            },
        }
        print(json.dumps(output_a, ensure_ascii=False, indent=2))
        return

    # ═══════════════════════════════════════════════════════
    # HUMANIZE (main mode)
    # ═══════════════════════════════════════════════════════
    if _HAS_RICH and _con and not use_json_flag:
        _print_banner()
        with _con.status(
            f"[bold bright_cyan]Humanizing ({args.lang}, {args.profile}, "
            f"intensity={args.intensity})...[/bold bright_cyan]",
            spinner="dots",
        ):
            t0 = time.perf_counter()
            result = humanize(
                text,
                lang=args.lang,
                profile=args.profile,
                intensity=args.intensity,
                preserve={"brand_terms": args.brand},
                constraints={
                    "max_change_ratio": args.max_change,
                    "keep_keywords": args.keep,
                },
                seed=args.seed,
            )
            elapsed = time.perf_counter() - t0

        _display_humanize_rich(result, text, args)
        _con.print(f"  [th.dim]Elapsed: {elapsed:.2f}s[/th.dim]\n")

        if args.output:
            try:
                with open(args.output, "w", encoding="utf-8") as f:
                    f.write(result.text)
                _con.print(f"  [th.ok]\u2714 Saved to {args.output}[/th.ok]")
            except Exception as e:
                _con.print(f"  [th.err]Error: {e}[/th.err]")
                sys.exit(1)
        else:
            print(result.text)

        if args.explain:
            report_text = explain(result)
            _con.print()
            _con.print(
                Panel(
                    report_text,
                    title="Change Report",
                    border_style="bright_blue",
                    box=box.ROUNDED,
                )
            )
    else:
        result = humanize(
            text,
            lang=args.lang,
            profile=args.profile,
            intensity=args.intensity,
            preserve={"brand_terms": args.brand},
            constraints={
                "max_change_ratio": args.max_change,
                "keep_keywords": args.keep,
            },
            seed=args.seed,
        )

        if args.output:
            try:
                with open(args.output, "w", encoding="utf-8") as f:
                    f.write(result.text)
                print(f"Saved to {args.output}", file=sys.stderr)
            except Exception as e:
                print(f"Error: {e}", file=sys.stderr)
                sys.exit(1)
        else:
            print(result.text)

        if args.explain:
            print("\n" + explain(result), file=sys.stderr)

    # ── Save report ──
    if args.report:
        report_data = {
            "lang": result.lang,
            "profile": result.profile,
            "intensity": result.intensity,
            "change_ratio": round(result.change_ratio, 4),
            "changes_count": len(result.changes),
            "changes": result.changes[:50],
            "metrics_before": result.metrics_before,
            "metrics_after": result.metrics_after,
        }
        try:
            with open(args.report, "w", encoding="utf-8") as f:
                json.dump(report_data, f, ensure_ascii=False, indent=2)
            msg = f"Report saved to {args.report}"
            if _con:
                _con.print(f"  [th.ok]\u2714 {msg}[/th.ok]")
            else:
                print(msg, file=sys.stderr)
        except Exception as e:
            msg = f"Error writing report: {e}"
            if _con:
                _con.print(f"[th.err]{msg}[/th.err]")
            else:
                print(msg, file=sys.stderr)


if __name__ == "__main__":
    main()
