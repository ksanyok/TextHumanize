"""Тесты параллельной обработки (P3.3)."""

from __future__ import annotations

from texthumanize import humanize_batch, humanize_chunked

_SAMPLE = (
    "Artificial intelligence is rapidly evolving. Neural networks process "
    "vast amounts of data efficiently. Machine learning enables automated "
    "problem-solving capabilities that were previously impossible."
)

_BATCH = [
    "The weather is nice today. Birds are singing outside.",
    "Technology advances rapidly. New tools emerge constantly.",
    "Education is important. Knowledge builds societies.",
    "Health matters greatly. Exercise improves wellbeing.",
]


class TestParallelBatch:
    """Tests for humanize_batch with max_workers."""

    def test_batch_sequential(self):
        results = humanize_batch(
            _BATCH, lang="en", intensity=30, max_workers=None
        )
        assert len(results) == 4
        for r in results:
            assert r.text

    def test_batch_parallel(self):
        results = humanize_batch(
            _BATCH, lang="en", intensity=30, max_workers=2
        )
        assert len(results) == 4
        for r in results:
            assert r.text

    def test_batch_parallel_preserves_order(self):
        results = humanize_batch(
            _BATCH, lang="en", intensity=30, max_workers=4, seed=42
        )
        assert len(results) == 4
        # Order must be preserved (result[i] corresponds to _BATCH[i])
        for i, r in enumerate(results):
            # Original must match input
            assert r.original == _BATCH[i]

    def test_batch_progress_callback(self):
        progress = []

        def on_progress(idx, total, result):
            progress.append((idx, total))

        results = humanize_batch(
            _BATCH, lang="en", intensity=30,
            max_workers=2, on_progress=on_progress,
        )
        assert len(results) == 4
        assert len(progress) == 4

    def test_batch_single_item_no_thread(self):
        results = humanize_batch(
            ["Hello world."], lang="en", intensity=30, max_workers=4
        )
        assert len(results) == 1

    def test_batch_deterministic_with_seed(self):
        r1 = humanize_batch(
            _BATCH[:2], lang="en", intensity=40, seed=100
        )
        r2 = humanize_batch(
            _BATCH[:2], lang="en", intensity=40, seed=100
        )
        for a, b in zip(r1, r2):
            assert a.text == b.text


class TestParallelChunked:
    """Tests for humanize_chunked with max_workers."""

    def test_chunked_sequential(self):
        long_text = "\n\n".join([_SAMPLE] * 10)
        result = humanize_chunked(
            long_text, chunk_size=200, lang="en", intensity=30,
        )
        assert result.text
        assert len(result.text) > 100

    def test_chunked_parallel(self):
        long_text = "\n\n".join([_SAMPLE] * 10)
        result = humanize_chunked(
            long_text, chunk_size=200, lang="en", intensity=30,
            max_workers=2,
        )
        assert result.text
        assert len(result.text) > 100

    def test_chunked_small_text_no_split(self):
        result = humanize_chunked(
            _SAMPLE, chunk_size=5000, lang="en", intensity=30,
            max_workers=4,
        )
        assert result.text

    def test_chunked_empty_text(self):
        result = humanize_chunked("", chunk_size=100, lang="en")
        assert result.text == ""

    def test_chunked_parallel_changes_collected(self):
        long_text = "\n\n".join([_SAMPLE] * 5)
        result = humanize_chunked(
            long_text, chunk_size=200, lang="en", intensity=50,
            max_workers=2,
        )
        # Changes from all chunks should be collected
        assert isinstance(result.changes, list)


class TestParallelPerformance:
    """Verify parallel processing doesn't break anything."""

    def test_parallel_vs_sequential_same_result(self):
        """Parallel and sequential should produce same results with same seed."""
        texts = _BATCH[:2]
        seq = humanize_batch(
            texts, lang="en", intensity=40, seed=77, max_workers=1
        )
        par = humanize_batch(
            texts, lang="en", intensity=40, seed=77, max_workers=2
        )
        for s, p in zip(seq, par):
            assert s.text == p.text

    def test_parallel_thread_safety(self):
        """Multiple parallel calls should not interfere."""
        results = humanize_batch(
            _BATCH * 2, lang="en", intensity=30, max_workers=4
        )
        assert len(results) == 8
        for r in results:
            assert r.text
            assert r.lang == "en"
