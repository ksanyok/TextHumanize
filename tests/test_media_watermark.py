"""Tests for the media (image/audio/video) watermark forensics engine.

Fixtures are built with the standard library only (no Pillow), so they run in
CI. The optional Pillow-based LSB analysis simply no-ops when Pillow is absent.
"""

from __future__ import annotations

import io
import struct
import time
import wave
import zlib

import texthumanize as th
from texthumanize.media_watermark import (
    _scan_markers,
    clean_media_watermarks,
    detect_media_watermarks,
    media_format,
)

# ── Pure-stdlib fixture builders ─────────────────────────────────────────────

def _png_chunk(ctype: bytes, data: bytes) -> bytes:
    return (
        struct.pack(">I", len(data))
        + ctype
        + data
        + struct.pack(">I", zlib.crc32(ctype + data) & 0xFFFFFFFF)
    )


def make_png(width: int = 16, height: int = 16, text: bytes | None = None) -> bytes:
    raw = b"".join(
        b"\x00" + bytes((x * 16 + y) % 256 for x in range(width * 3))
        for y in range(height)
    )
    ihdr = struct.pack(">IIBBBBB", width, height, 8, 2, 0, 0, 0)  # 8-bit RGB
    out = b"\x89PNG\r\n\x1a\n" + _png_chunk(b"IHDR", ihdr)
    if text is not None:
        out += _png_chunk(b"tEXt", text)
    out += _png_chunk(b"IDAT", zlib.compress(raw)) + _png_chunk(b"IEND", b"")
    return out


def make_wav(software: str | None = None) -> bytes:
    buf = io.BytesIO()
    with wave.open(buf, "wb") as wf:
        wf.setnchannels(1)
        wf.setsampwidth(2)
        wf.setframerate(8000)
        wf.writeframes(b"\x00\x10" * 4000)
    data = bytearray(buf.getvalue())
    if software is not None:
        payload = software.encode() + b"\x00"
        if len(payload) % 2:
            payload += b"\x00"
        isft = b"ISFT" + struct.pack("<I", len(payload)) + payload
        info = b"INFO" + isft
        listc = b"LIST" + struct.pack("<I", len(info)) + info
        data[4:8] = struct.pack("<I", struct.unpack("<I", data[4:8])[0] + len(listc))
        data += listc
    return bytes(data)


def make_mp4_with_marker(marker: bytes) -> bytes:
    ftyp = struct.pack(">I", 24) + b"ftyp" + b"mp42" + b"\x00\x00\x00\x00" + b"mp42isom"
    payload = marker.ljust(32, b"\x00")
    uuid = struct.pack(">I", len(payload) + 8) + b"uuid" + payload
    return ftyp + uuid


# ── Format detection ─────────────────────────────────────────────────────────

class TestFormatDetection:
    def test_magic_bytes(self) -> None:
        assert media_format(make_png()) == "png"
        assert media_format(make_wav()) == "wav"
        assert media_format(make_mp4_with_marker(b"x")) == "mp4"
        assert media_format(b"\xff\xd8\xff\xe0\x00\x10JFIF\x00\x01") == "jpeg"
        assert media_format(b"GIF89a" + b"\x00" * 10) == "gif"
        assert media_format(b"not a media file at all") == "unknown"


# ── Images (PNG) ─────────────────────────────────────────────────────────────

class TestPngForensics:
    def test_clean_png_has_no_watermark(self) -> None:
        report = detect_media_watermarks(make_png())
        assert report["schema_version"] == "text-humanize.media_watermark_report.v1"
        assert report["media_type"] == "image"
        assert report["has_watermarks"] is False

    def test_sd_metadata_detected(self) -> None:
        text = b"parameters\x00Steps: 20, Sampler: Euler a, CFG scale: 7, Seed: 1, Stable Diffusion"
        report = detect_media_watermarks(make_png(text=text))
        assert report["has_watermarks"] is True
        assert report["risk_score"] >= 0.9
        types = {f["type"] for f in report["findings"]}
        assert "embedded_generation_parameters" in types
        assert "generator_signature" in types
        assert any(f.get("generator") == "Stable Diffusion" for f in report["findings"])
        assert report["removable"] is True

    def test_clean_strips_metadata_and_keeps_valid_png(self) -> None:
        text = b"parameters\x00Stable Diffusion prompt here"
        png = make_png(text=text)
        result = clean_media_watermarks(png)
        assert result["changed"] is True
        assert result["bytes_removed"] > 0
        # Cleaned output is watermark-free and still a valid PNG chunk stream.
        after = detect_media_watermarks(result["bytes"])
        assert after["has_watermarks"] is False
        assert result["bytes"].startswith(b"\x89PNG\r\n\x1a\n")
        assert result["bytes"].rstrip().endswith(
            b"IEND" + struct.pack(">I", zlib.crc32(b"IEND") & 0xFFFFFFFF)
        )

    def test_c2pa_marker_high_severity(self) -> None:
        text = b"Comment\x00contains c2pa manifest content"
        report = detect_media_watermarks(make_png(text=text))
        assert any(f["category"] == "c2pa" for f in report["findings"])


# ── Audio (WAV) ──────────────────────────────────────────────────────────────

class TestWavForensics:
    def test_clean_wav(self) -> None:
        report = detect_media_watermarks(make_wav())
        assert report["media_type"] == "audio"
        assert report["has_watermarks"] is False

    def test_software_signature_detected_and_removed(self) -> None:
        wav = make_wav(software="Suno")
        report = detect_media_watermarks(wav)
        assert report["has_watermarks"] is True
        assert any(f.get("generator") == "Suno (audio)" for f in report["findings"])
        result = clean_media_watermarks(wav)
        assert result["changed"] is True
        assert detect_media_watermarks(result["bytes"])["has_watermarks"] is False

    def test_studio_and_audio_words_are_not_udio(self) -> None:
        # Human recordings: DAW names and XMP audio fields contain "udio" as a substring.
        for software in ("FL Studio 21", "Studio One 6", "Sound Studio", "xmpDM:audioSampleRate"):
            report = detect_media_watermarks(make_wav(software=software))
            assert report["has_watermarks"] is False, software

    def test_common_words_need_generator_context(self) -> None:
        for software in ("Runway Lights (live)", "Firefly - demo take", "Influx mixdown",
                         "Gemini Records", "Playground session", "Pikachu remix"):
            report = detect_media_watermarks(make_wav(software=software))
            assert report["has_watermarks"] is False, software

    def test_sample_data_is_not_scanned(self) -> None:
        # The PCM "data" chunk is audio, not metadata: a chance byte run there must not count,
        # and a large file must not spend seconds in regex over samples.
        wav = make_wav()
        body = b"\x00suno\x00" + bytes(4 * 1024 * 1024)
        head = wav[:wav.index(b"data")]
        big = head + b"data" + struct.pack("<I", len(body)) + body
        big = b"RIFF" + struct.pack("<I", len(big) - 8) + big[8:]
        start = time.perf_counter()
        report = detect_media_watermarks(big)
        assert report["has_watermarks"] is False
        assert time.perf_counter() - start < 2.0

    def test_vorbis_comment_value_is_a_signature(self) -> None:
        # OGG/FLAC: "software=Udio" ends at a length-prefixed boundary (next field length or framing byte \x01).
        hits = {f.get("generator") for f in _scan_markers(b"\x0d\x00\x00\x00TIST=Meydan\r\x00\x00\x00software=Udio\x01\x05vorbis")}
        assert "Udio (audio)" in hits
        hits = {f.get("generator") for f in _scan_markers(b"\x0e\x00\x00\x00encoder=Suno\x0b\x00\x00\x00")}
        assert "Suno (audio)" in hits
        for blob in (b"title=Udio Studio take\x01", b"comment=FL Studio\x01", b"album=Sunology\x01"):
            assert not _scan_markers(blob), blob

    def test_generators_with_context_still_detected(self) -> None:
        cases = {
            "Made with Udio": "Udio (audio)",
            "Udio": "Udio (audio)",
            "https://suno.com/song/abc": "Suno (audio)",
            "Suno AI v4.5": "Suno (audio)",
            "FLUX.1-dev": "FLUX (Black Forest Labs)",
            "OpenAI Sora": "OpenAI Sora",
            "Runway Gen-4": "Runway",
            "ElevenLabs": "ElevenLabs (audio)",
        }
        for software, label in cases.items():
            report = detect_media_watermarks(make_wav(software=software))
            gens = {f.get("generator") for f in report["findings"]}
            assert label in gens, (software, gens)


# ── Video (MP4) — detection + honest removal guidance ───────────────────────

class TestMp4Forensics:
    def test_c2pa_detected_removal_guided(self) -> None:
        mp4 = make_mp4_with_marker(b"c2pa manifest trainedAlgorithmicMedia")
        report = detect_media_watermarks(mp4)
        assert report["media_type"] == "video"
        assert report["has_watermarks"] is True
        assert report["removable"] is False
        result = clean_media_watermarks(mp4)
        assert result["changed"] is False
        assert "ffmpeg" in result["note"]


# ── API surface + safety ─────────────────────────────────────────────────────

class TestApiSurface:
    def test_public_exports(self) -> None:
        for name in ("detect_media_watermarks", "clean_media_watermarks",
                     "media_watermark_report", "media_format"):
            assert hasattr(th, name)
            assert name in th.__all__

    def test_report_alias(self) -> None:
        assert th.media_watermark_report(make_png())["format"] == "png"

    def test_honest_synthid_note(self) -> None:
        report = detect_media_watermarks(make_png(text=b"parameters\x00Stable Diffusion"))
        assert any("SynthID" in a for a in report["suggested_actions"])

    def test_unknown_bytes_graceful(self) -> None:
        report = detect_media_watermarks(b"hello world not media")
        assert report["format"] == "unknown"
        assert report["has_watermarks"] is False
