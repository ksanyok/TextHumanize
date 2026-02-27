"""TextHumanize + FastAPI — async endpoints with validation.

Install:
    pip install texthumanize fastapi uvicorn

Run:
    uvicorn examples.fastapi_integration:app --host 0.0.0.0 --port 8000
"""

from __future__ import annotations

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field

from texthumanize import async_detect_ai, async_humanize

app = FastAPI(
    title="TextHumanize API",
    version="1.0.0",
    description="Text humanization and AI detection via FastAPI",
)


class HumanizeRequest(BaseModel):
    text: str = Field(..., min_length=1, max_length=1_000_000)
    lang: str = Field("auto")
    profile: str = Field("web")
    intensity: int = Field(60, ge=0, le=100)
    seed: int | None = None


class DetectRequest(BaseModel):
    text: str = Field(..., min_length=1, max_length=1_000_000)
    lang: str = Field("auto")


@app.post("/humanize")
async def humanize_endpoint(req: HumanizeRequest):
    """Humanize text using the 17-stage pipeline."""
    try:
        result = await async_humanize(
            req.text,
            lang=req.lang,
            profile=req.profile,
            intensity=req.intensity,
            seed=req.seed,
        )
        return {
            "text": result.text,
            "change_ratio": result.change_ratio,
            "quality_score": getattr(result, "quality_score", 0.0),
            "lang": result.lang,
        }
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@app.post("/detect-ai")
async def detect_ai_endpoint(req: DetectRequest):
    """Detect AI-generated text."""
    try:
        result = await async_detect_ai(req.text, lang=req.lang)
        return {
            "score": result["score"],
            "verdict": result["verdict"],
            "confidence": result["confidence"],
        }
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@app.get("/health")
async def health():
    return {"status": "ok"}
