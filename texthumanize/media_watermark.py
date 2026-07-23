"""Media watermark & provenance forensics for images, audio and video.

A pure-Python (stdlib + numpy), offline engine that inspects media files for
AI-watermark and provenance signals and can strip the removable ones:

* **Provenance metadata** — C2PA / CAI manifests, XMP (`digitalSourceType`,
  `trainedAlgorithmicMedia`, GenAI fields), EXIF `Software`/`Make`, and
  embedded generation parameters (Stable Diffusion, ComfyUI, etc.).
* **Generator signatures** — known markers from Midjourney, DALL·E, Stable
  Diffusion, Adobe Firefly, Leonardo, NovelAI, Google, and more.
* **Statistical anomalies** — LSB steganography in images (optional, needs
  Pillow) and out-of-band / ultrasonic energy in audio (WAV via stdlib).

Honest limits — read before relying on this:

* Detection covers **inspectable** signals. It cannot detect robust neural
  watermarks such as Google **SynthID**, which are embedded in the content
  itself and are not exposed through metadata.
* Removal strips provenance metadata and ancillary data and re-serialises the
  container. It does **not** remove in-content neural watermarks; those are
  designed to survive metadata stripping and re-encoding. Treat this as a
  provenance/forensics and metadata-privacy tool, not a guarantee of erasing
  every watermark.
"""

from __future__ import annotations

import struct
from pathlib import Path
from typing import Any

__all__ = [
    "clean_media_watermarks",
    "detect_media_watermarks",
    "media_watermark_report",
    "media_format",
]

_SCHEMA = "text-humanize.media_watermark_report.v1"

# Markers (lowercased) that indicate AI provenance / generators when found in
# textual metadata. Maps marker -> human label.
_GENERATOR_SIGNATURES: dict[str, str] = {
    "stable diffusion": "Stable Diffusion",
    "stablediffusion": "Stable Diffusion",
    "automatic1111": "AUTOMATIC1111 (Stable Diffusion)",
    "comfyui": "ComfyUI (Stable Diffusion)",
    "invokeai": "InvokeAI (Stable Diffusion)",
    "midjourney": "Midjourney",
    "dall-e": "DALL·E (OpenAI)",
    "dall·e": "DALL·E (OpenAI)",
    "dalle": "DALL·E (OpenAI)",
    "openai": "OpenAI",
    "firefly": "Adobe Firefly",
    "adobe firefly": "Adobe Firefly",
    "leonardo.ai": "Leonardo.Ai",
    "leonardo ai": "Leonardo.Ai",
    "novelai": "NovelAI",
    "playground": "Playground AI",
    "ideogram": "Ideogram",
    "flux": "FLUX (Black Forest Labs)",
    "imagen": "Google Imagen",
    "synthid": "Google SynthID (declared)",
    "gemini": "Google Gemini",
    "runway": "Runway",
    "sora": "OpenAI Sora",
    "kling": "Kling AI",
    "pika": "Pika",
    "elevenlabs": "ElevenLabs (audio)",
    "suno": "Suno (audio)",
    "udio": "Udio (audio)",
    # 2026 additions — distinctive tokens only.
    "recraft": "Recraft",
    "seedream": "Seedream (ByteDance)",
    "seedance": "Seedance (ByteDance)",
    "hunyuanvideo": "Hunyuan (Tencent)",
    "nano-banana": "Gemini Nano Banana (Google)",
    "reve.art": "Reve",
    "stable-signature": "Meta Stable Signature (declared)",
    "trainedalgorithmic": "AI-generated (IPTC digitalSourceType)",
}

# C2PA / provenance standard markers (case-insensitive byte search).
_PROVENANCE_MARKERS: dict[bytes, str] = {
    b"c2pa": "C2PA manifest (Content Credentials)",
    b"jumbf": "JUMBF box (C2PA/JPEG provenance)",
    b"contentauth": "Content Authenticity Initiative (CAI)",
    b"trainedalgorithmicmedia": "XMP digitalSourceType: trainedAlgorithmicMedia (AI-generated)",
    b"compositewithtrainedalgorithmicmedia": "XMP digitalSourceType: AI-composited",
    b"digitalsourcetype": "XMP digitalSourceType (provenance)",
    b"http://ns.adobe.com/xap": "XMP packet",
}

# Magic-byte format detection.
_IMAGE_FORMATS = {"png", "jpeg", "gif", "webp", "bmp", "tiff"}
_AUDIO_FORMATS = {"wav", "mp3", "flac", "ogg"}
_VIDEO_FORMATS = {"mp4", "mkv", "avi"}


def _read_source(source: str | bytes | Path) -> bytes:
    if isinstance(source, (bytes, bytearray)):
        return bytes(source)
    path = Path(source)
    return path.read_bytes()


def media_format(data: bytes) -> str:
    """Return a coarse media format string from magic bytes, or 'unknown'."""
    if len(data) < 12:
        return "unknown"
    if data[:8] == b"\x89PNG\r\n\x1a\n":
        return "png"
    if data[:3] == b"\xff\xd8\xff":
        return "jpeg"
    if data[:6] in (b"GIF87a", b"GIF89a"):
        return "gif"
    if data[:4] == b"RIFF" and data[8:12] == b"WEBP":
        return "webp"
    if data[:4] == b"RIFF" and data[8:12] == b"WAVE":
        return "wav"
    if data[:4] == b"RIFF" and data[8:12] == b"AVI ":
        return "avi"
    if data[:2] == b"BM":
        return "bmp"
    if data[:4] in (b"II*\x00", b"MM\x00*"):
        return "tiff"
    if data[:3] == b"ID3" or data[:2] in (b"\xff\xfb", b"\xff\xf3", b"\xff\xf2"):
        return "mp3"
    if data[:4] == b"fLaC":
        return "flac"
    if data[:4] == b"OggS":
        return "ogg"
    if data[4:8] == b"ftyp":
        return "mp4"
    if data[:4] == b"\x1a\x45\xdf\xa3":
        return "mkv"
    return "unknown"


def _media_type_for(fmt: str) -> str:
    if fmt in _IMAGE_FORMATS:
        return "image"
    if fmt in _AUDIO_FORMATS:
        return "audio"
    if fmt in _VIDEO_FORMATS:
        return "video"
    return "unknown"


# ─────────────────────────────────────────────────────────────
#  Generic helpers
# ─────────────────────────────────────────────────────────────

def _scan_markers(blob: bytes) -> list[dict[str, Any]]:
    """Scan a metadata blob for provenance and generator markers."""
    findings: list[dict[str, Any]] = []
    low = blob.lower()
    for marker, label in _PROVENANCE_MARKERS.items():
        if marker in low:
            findings.append({
                "type": "provenance_metadata",
                "category": "c2pa" if b"c2pa" in marker or b"jumbf" in marker or b"contentauth" in marker else "xmp",
                "severity": "high" if (b"c2pa" in marker or b"trained" in marker) else "medium",
                "detail": label,
            })
    for signature, label in _GENERATOR_SIGNATURES.items():
        if signature.encode("utf-8") in low:
            findings.append({
                "type": "generator_signature",
                "category": "generator",
                "severity": "high",
                "detail": f"Generator signature: {label}",
                "generator": label,
            })
    return findings


def _dedupe(findings: list[dict[str, Any]]) -> list[dict[str, Any]]:
    seen: set[tuple] = set()
    out: list[dict[str, Any]] = []
    for f in findings:
        key = (f.get("type"), f.get("detail"))
        if key in seen:
            continue
        seen.add(key)
        out.append(f)
    return out


# ─────────────────────────────────────────────────────────────
#  PNG
# ─────────────────────────────────────────────────────────────

def _iter_png_chunks(data: bytes):
    pos = 8
    n = len(data)
    while pos + 8 <= n:
        length = struct.unpack(">I", data[pos:pos + 4])[0]
        ctype = data[pos + 4:pos + 8]
        start = pos + 8
        end = start + length
        if end > n:
            break
        yield ctype, data[start:end], pos, end + 4  # +4 CRC
        pos = end + 4


_PNG_TEXT_CHUNKS = {b"tEXt", b"zTXt", b"iTXt"}
# Chunk keywords essentially unique to image-generation tooling — the key name
# alone is conclusive. Maps key -> the tool it identifies.
_PNG_STRONG_KEYS = {
    "parameters": "AUTOMATIC1111 / Forge / Fooocus (Stable Diffusion)",
    "workflow": "ComfyUI (Stable Diffusion)",
    "sd-metadata": "InvokeAI (Stable Diffusion)",
    "invokeai_metadata": "InvokeAI (Stable Diffusion)",
    "sui_image_params": "SwarmUI (Stable Diffusion)",
    "dream": "InvokeAI (Stable Diffusion)",
    "negative prompt": "Stable Diffusion",
}
# Generic keywords (prompt/comment/software/title/description/author) are NOT
# treated as AI on the key name alone — a camera caption in Description or a
# Photoshop Comment used to be misread as AI. They count only when the VALUE
# carries an actual generation-parameter hint below.
_PNG_PARAM_HINTS = (
    "steps:", "sampler", "cfg scale", "model hash", "denoising_strength",
    "class_type", "sampler_name", '"scheduler"', "negative prompt:",
)


def _parse_png(data: bytes) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    findings: list[dict[str, Any]] = []
    meta: dict[str, Any] = {"format": "png", "text_chunks": []}
    for ctype, payload, _start, _end in _iter_png_chunks(data):
        if ctype in _PNG_TEXT_CHUNKS:
            text = payload.replace(b"\x00", b" ").decode("latin-1", "replace")
            key = text.split(" ", 1)[0].strip().lower()
            meta["text_chunks"].append(text[:200])
            strong = _PNG_STRONG_KEYS.get(key)
            has_hint = any(k in text.lower() for k in _PNG_PARAM_HINTS)
            if strong or has_hint:
                findings.append({
                    "type": "embedded_generation_parameters",
                    "category": "generation_params",
                    "severity": "high",
                    "detail": (f"PNG {ctype.decode()} '{key}' chunk — {strong}"
                               if strong else
                               f"PNG {ctype.decode()} chunk with Stable Diffusion generation parameters"),
                    **({"generator": strong} if strong else {}),
                })
            findings.extend(_scan_markers(payload))
        elif ctype in (b"eXIf", b"caBX", b"iDOT"):
            findings.extend(_scan_markers(payload))
            if ctype == b"caBX":
                findings.append({
                    "type": "provenance_metadata", "category": "c2pa",
                    "severity": "high", "detail": "PNG caBX chunk (C2PA manifest box)",
                })
    return findings, meta


def _clean_png(data: bytes) -> bytes:
    """Re-serialise PNG keeping only image-critical chunks."""
    keep = {b"IHDR", b"PLTE", b"IDAT", b"IEND", b"tRNS", b"gAMA", b"cHRM",
            b"sRGB", b"iCCP", b"bKGD", b"pHYs", b"sBIT", b"acTL", b"fcTL", b"fdAT"}
    out = bytearray(data[:8])
    for ctype, payload, _s, _e in _iter_png_chunks(data):
        if ctype in keep:
            out += struct.pack(">I", len(payload)) + ctype + payload
            import zlib
            out += struct.pack(">I", zlib.crc32(ctype + payload) & 0xFFFFFFFF)
    if not out[-8:].endswith(b"IEND" + struct.pack(">I", zlib.crc32(b"IEND") & 0xFFFFFFFF)):
        # ensure IEND present
        if b"IEND" not in bytes(out[-12:]):
            import zlib as _z
            out += struct.pack(">I", 0) + b"IEND" + struct.pack(">I", _z.crc32(b"IEND") & 0xFFFFFFFF)
    return bytes(out)


# ─────────────────────────────────────────────────────────────
#  JPEG
# ─────────────────────────────────────────────────────────────

def _iter_jpeg_segments(data: bytes):
    pos = 2
    n = len(data)
    while pos + 4 <= n:
        if data[pos] != 0xFF:
            pos += 1
            continue
        marker = data[pos + 1]
        if marker in (0xD8, 0xD9) or 0xD0 <= marker <= 0xD7:
            pos += 2
            continue
        if marker == 0xDA:  # SOS — image data follows; stop scanning headers
            yield marker, b"", pos
            break
        seg_len = struct.unpack(">H", data[pos + 2:pos + 4])[0]
        payload = data[pos + 4:pos + 2 + seg_len]
        yield marker, payload, pos
        pos += 2 + seg_len


def _parse_jpeg(data: bytes) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    findings: list[dict[str, Any]] = []
    meta: dict[str, Any] = {"format": "jpeg", "app_segments": []}
    for marker, payload, _pos in _iter_jpeg_segments(data):
        if 0xE0 <= marker <= 0xEF or marker == 0xFE:  # APPn or COM
            meta["app_segments"].append(f"APP{marker - 0xE0}" if marker != 0xFE else "COM")
            findings.extend(_scan_markers(payload))
            if marker == 0xEB or b"JUMBF" in payload or b"jumb" in payload:
                if b"c2pa" in payload.lower() or marker == 0xEB:
                    findings.append({
                        "type": "provenance_metadata", "category": "c2pa",
                        "severity": "high",
                        "detail": "JPEG APP11/JUMBF segment (C2PA provenance)",
                    })
            if payload[:6] == b"Exif\x00\x00":
                if b"software" in payload.lower():
                    findings.extend(_scan_markers(payload))
    return findings, meta


def _clean_jpeg(data: bytes) -> bytes:
    """Strip APPn (except essential APP0 JFIF) and COM segments."""
    out = bytearray(b"\xff\xd8")  # SOI
    pos = 2
    n = len(data)
    while pos + 4 <= n:
        if data[pos] != 0xFF:
            out.append(data[pos])
            pos += 1
            continue
        marker = data[pos + 1]
        if marker == 0xDA:  # SOS — copy rest verbatim
            out += data[pos:]
            break
        if marker in (0xD8, 0xD9) or 0xD0 <= marker <= 0xD7:
            out += data[pos:pos + 2]
            pos += 2
            continue
        seg_len = struct.unpack(">H", data[pos + 2:pos + 4])[0]
        seg = data[pos:pos + 2 + seg_len]
        payload = data[pos + 4:pos + 2 + seg_len]
        # Drop EXIF/XMP/C2PA/comment; keep JFIF APP0 and core tables.
        drop = (0xE1 <= marker <= 0xEF) or marker == 0xFE
        keep_app0 = marker == 0xE0 and payload[:5] == b"JFIF\x00"
        if drop and not keep_app0:
            pos += 2 + seg_len
            continue
        out += seg
        pos += 2 + seg_len
    return bytes(out)


# ─────────────────────────────────────────────────────────────
#  RIFF (WebP, WAV, AVI)
# ─────────────────────────────────────────────────────────────

def _iter_riff_chunks(data: bytes):
    pos = 12
    n = len(data)
    while pos + 8 <= n:
        cid = data[pos:pos + 4]
        size = struct.unpack("<I", data[pos + 4:pos + 8])[0]
        start = pos + 8
        end = start + size
        if end > n:
            break
        yield cid, data[start:end], pos, end
        pos = end + (size & 1)  # padding to even


def _parse_riff(data: bytes, fmt: str) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    findings: list[dict[str, Any]] = []
    meta: dict[str, Any] = {"format": fmt, "chunks": []}
    for cid, payload, _s, _e in _iter_riff_chunks(data):
        cid_s = cid.decode("latin-1", "replace").strip()
        meta["chunks"].append(cid_s)
        if cid in (b"EXIF", b"XMP ", b"XML ", b"LIST", b"INFO", b"C2PA", b"caBX", b"id3 ", b"ID3 "):
            findings.extend(_scan_markers(payload))
        else:
            findings.extend(_scan_markers(payload))
        if cid in (b"C2PA", b"caBX"):
            findings.append({
                "type": "provenance_metadata", "category": "c2pa",
                "severity": "high", "detail": f"RIFF {cid_s} chunk (C2PA provenance)",
            })
    return findings, meta


def _clean_riff(data: bytes, fmt: str) -> bytes:
    """Keep only essential chunks; drop metadata/provenance."""
    if fmt == "webp":
        keep = {b"VP8 ", b"VP8L", b"VP8X", b"ANIM", b"ANMF", b"ALPH", b"ICCP"}
    elif fmt == "wav":
        keep = {b"fmt ", b"data", b"fact"}
    else:
        keep = None  # avi: don't rewrite (complex index); return as-is
    if keep is None:
        return data
    body = bytearray()
    for cid, payload, _s, _e in _iter_riff_chunks(data):
        if cid in keep:
            body += cid + struct.pack("<I", len(payload)) + payload
            if len(payload) & 1:
                body += b"\x00"
    riff_type = data[8:12]
    out = b"RIFF" + struct.pack("<I", len(body) + 4) + riff_type + bytes(body)
    return out


# ─────────────────────────────────────────────────────────────
#  ISO BMFF (MP4 / MOV) and Matroska — detection only
# ─────────────────────────────────────────────────────────────

def _parse_mp4(data: bytes) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    findings: list[dict[str, Any]] = []
    meta: dict[str, Any] = {"format": "mp4", "atoms": []}

    def walk(buf: bytes, base: int, depth: int) -> None:
        pos = 0
        n = len(buf)
        while pos + 8 <= n:
            size = struct.unpack(">I", buf[pos:pos + 4])[0]
            atom = buf[pos + 4:pos + 8]
            header = 8
            if size == 1 and pos + 16 <= n:
                size = struct.unpack(">Q", buf[pos + 8:pos + 16])[0]
                header = 16
            if size == 0:
                size = n - pos
            if size < header or pos + size > n:
                break
            payload = buf[pos + header:pos + size]
            if depth == 0:
                meta["atoms"].append(atom.decode("latin-1", "replace"))
            if atom in (b"uuid", b"meta", b"udta", b"Xtra", b"keys", b"ilst", b"data"):
                findings.extend(_scan_markers(payload))
            if atom in (b"moov", b"udta", b"meta", b"trak", b"mdia", b"minf", b"stbl"):
                sub = payload[4:] if atom == b"meta" else payload
                if depth < 4:
                    walk(sub, base + pos + header, depth + 1)
            pos += size

    walk(data, 0, 0)
    findings.extend(_scan_markers(data[:65536]))  # header region sweep
    return _dedupe(findings), meta


def _parse_matroska(data: bytes) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    # EBML parsing is involved; do a bounded marker sweep of the header region.
    findings = _scan_markers(data[:131072])
    return _dedupe(findings), {"format": "mkv"}


# ─────────────────────────────────────────────────────────────
#  Statistical analysis
# ─────────────────────────────────────────────────────────────

def _image_lsb_analysis(data: bytes) -> dict[str, Any] | None:
    """Chi-square LSB-uniformity test for steganographic payloads.

    Needs Pillow to decode arbitrary formats; returns None if unavailable.
    """
    try:
        import io

        import numpy as np
        from PIL import Image
    except Exception:
        return None
    try:
        img = Image.open(io.BytesIO(data)).convert("RGB")
        arr = np.asarray(img, dtype=np.uint8).ravel()
    except Exception:
        return None
    if arr.size < 1024:
        return None
    lsb = arr & 1
    ones = float(lsb.mean())
    # Under no hidden payload, natural-image LSBs are NOT perfectly uniform.
    # Steganography pushes the LSB distribution toward 0.5 across the plane.
    # Chi-square against expected 0.5 on byte-value pairs (sample-pairs style).
    n = lsb.size
    observed_ones = int(lsb.sum())
    expected = n / 2.0
    chi = ((observed_ones - expected) ** 2) / expected + ((n - observed_ones - expected) ** 2) / expected
    # Very low chi (near-perfect 0.5) over a large plane is suspicious.
    suspicious = bool(abs(ones - 0.5) < 0.002 and n > 200000)
    return {
        "available": True,
        "lsb_ones_ratio": round(ones, 5),
        "chi_square": round(float(chi), 3),
        "samples": int(n),
        "lsb_anomaly": suspicious,
    }


def _audio_spectral_analysis(data: bytes, fmt: str) -> dict[str, Any] | None:
    """Out-of-band / ultrasonic energy probe for WAV audio (stdlib + numpy)."""
    if fmt != "wav":
        return None
    try:
        import io
        import wave

        import numpy as np
    except Exception:
        return None
    try:
        with wave.open(io.BytesIO(data), "rb") as wf:
            framerate = wf.getframerate()
            nframes = min(wf.getnframes(), framerate * 20)  # cap 20s
            sampwidth = wf.getsampwidth()
            channels = wf.getnchannels()
            raw = wf.readframes(nframes)
    except Exception:
        return None
    if sampwidth != 2 or not raw:
        return {"available": True, "note": "Only 16-bit PCM analysed", "high_band_anomaly": False}
    samples = np.frombuffer(raw, dtype=np.int16).astype(np.float64)
    if channels > 1:
        samples = samples[::channels]
    if samples.size < 2048:
        return None
    samples -= samples.mean()
    spectrum = np.abs(np.fft.rfft(samples * np.hanning(samples.size)))
    total = float(spectrum.sum()) or 1.0
    nyq = framerate / 2.0
    freqs = np.fft.rfftfreq(samples.size, 1.0 / framerate)
    # Energy in the top 10% of the band (often empty in natural speech/music;
    # some audio watermarks/steg sit near Nyquist or in ultrasonic ranges).
    high_mask = freqs >= (0.9 * nyq)
    high_ratio = float(spectrum[high_mask].sum() / total)
    return {
        "available": True,
        "sample_rate": framerate,
        "high_band_energy_ratio": round(high_ratio, 5),
        "high_band_anomaly": bool(high_ratio > 0.02),
    }


# ─────────────────────────────────────────────────────────────
#  Public API
# ─────────────────────────────────────────────────────────────

_REMOVABLE_FORMATS = {"png", "jpeg", "webp", "wav"}


def detect_media_watermarks(
    source: str | bytes | Path,
    media_type: str = "auto",
) -> dict[str, Any]:
    """Detect AI-watermark and provenance signals in an image/audio/video file.

    Args:
        source: A file path or raw bytes.
        media_type: ``"auto"`` (default) or one of ``image``/``audio``/``video``
            to assert the expected category.

    Returns:
        A ``text-humanize.media_watermark_report.v1`` dict.
    """
    data = _read_source(source)
    fmt = media_format(data)
    detected_type = _media_type_for(fmt)

    findings: list[dict[str, Any]] = []
    meta: dict[str, Any] = {"format": fmt}
    statistical: dict[str, Any] = {}

    if fmt == "png":
        findings, meta = _parse_png(data)
        stat = _image_lsb_analysis(data)
        if stat:
            statistical["image_lsb"] = stat
    elif fmt == "jpeg":
        findings, meta = _parse_jpeg(data)
        stat = _image_lsb_analysis(data)
        if stat:
            statistical["image_lsb"] = stat
    elif fmt in ("webp", "wav", "avi"):
        findings, meta = _parse_riff(data, fmt)
        if fmt == "wav":
            stat = _audio_spectral_analysis(data, fmt)
            if stat:
                statistical["audio_spectral"] = stat
        elif fmt == "webp":
            stat = _image_lsb_analysis(data)
            if stat:
                statistical["image_lsb"] = stat
    elif fmt == "mp4":
        findings, meta = _parse_mp4(data)
    elif fmt == "mkv":
        findings, meta = _parse_matroska(data)
    elif fmt in ("gif", "bmp", "tiff", "mp3", "flac", "ogg"):
        # Generic marker sweep for formats without a dedicated parser yet.
        findings = _scan_markers(data[:262144])
    else:
        findings = _scan_markers(data[:262144])

    # Fold statistical anomalies into findings.
    if statistical.get("image_lsb", {}).get("lsb_anomaly"):
        findings.append({
            "type": "statistical_anomaly", "category": "steganography",
            "severity": "medium",
            "detail": "Image LSB plane is abnormally uniform (possible steganographic payload).",
        })
    if statistical.get("audio_spectral", {}).get("high_band_anomaly"):
        findings.append({
            "type": "statistical_anomaly", "category": "spectral",
            "severity": "medium",
            "detail": "Unusual high-frequency energy (possible audio watermark/steganography).",
        })

    findings = _dedupe(findings)
    has = bool(findings)
    severity_weight = {"high": 1.0, "medium": 0.6, "low": 0.3}
    risk = max((severity_weight.get(f.get("severity", "low"), 0.3) for f in findings), default=0.0)

    removable = fmt in _REMOVABLE_FORMATS
    actions: list[str] = []
    if has and removable:
        actions.append("Use clean_media_watermarks() to strip the detected metadata/provenance and re-serialise the file.")
    if has and not removable:
        actions.append(
            f"Metadata stripping for {fmt} is best done with a container tool "
            f"(e.g. `ffmpeg -i in.{fmt} -map_metadata -1 -c copy out.{fmt}`)."
        )
    if any(f.get("type") == "generator_signature" for f in findings):
        actions.append("A generator signature was found in metadata; confirm provenance before publishing.")
    actions.append(
        "Note: this audit covers inspectable metadata and statistical signals. "
        "It cannot detect robust neural watermarks such as Google SynthID."
    )

    return {
        "schema_version": _SCHEMA,
        "media_type": detected_type if media_type == "auto" else media_type,
        "format": fmt,
        "has_watermarks": has,
        "risk_score": round(risk, 3),
        "findings": findings,
        "metadata": meta,
        "statistical": statistical,
        "removable": removable,
        "suggested_actions": actions,
    }


def media_watermark_report(source: str | bytes | Path) -> dict[str, Any]:
    """Alias for :func:`detect_media_watermarks` (full report)."""
    return detect_media_watermarks(source)


def clean_media_watermarks(
    source: str | bytes | Path,
    media_type: str = "auto",
    *,
    output: str | Path | None = None,
) -> dict[str, Any]:
    """Strip removable provenance/metadata and re-serialise the media file.

    Reliable for PNG, JPEG, WebP and WAV (metadata/ancillary chunks removed).
    For other containers (MP4/MKV/AVI/…) the original bytes are returned with a
    note, because safe removal requires a full container rewrite (use ffmpeg).

    Returns a dict with the cleaned ``bytes``, ``changed`` flag, ``bytes_removed``
    and an honest note about neural watermarks. If ``output`` is given the bytes
    are also written there.
    """
    data = _read_source(source)
    fmt = media_format(data)
    cleaned = data
    note = ""
    if fmt == "png":
        cleaned = _clean_png(data)
    elif fmt == "jpeg":
        cleaned = _clean_jpeg(data)
    elif fmt in ("webp", "wav"):
        cleaned = _clean_riff(data, fmt)
    else:
        note = (
            f"In-place metadata stripping is not implemented for {fmt}; "
            f"use `ffmpeg -i in.{fmt} -map_metadata -1 -c copy out.{fmt}`."
        )

    changed = cleaned != data
    if output is not None and changed:
        Path(output).write_bytes(cleaned)

    return {
        "schema_version": "text-humanize.media_clean.v1",
        "format": fmt,
        "changed": changed,
        "bytes_before": len(data),
        "bytes_after": len(cleaned),
        "bytes_removed": len(data) - len(cleaned),
        "bytes": cleaned,
        "note": note or (
            "Provenance metadata stripped. This does not remove robust in-content "
            "neural watermarks (e.g. SynthID), which survive metadata removal."
        ),
    }
