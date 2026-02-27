# FastAPI Integration

Full async integration with FastAPI using TextHumanize's async API.

## Installation

```bash
pip install texthumanize fastapi uvicorn
```

## Complete Example

```python
"""TextHumanize + FastAPI — async endpoints."""
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field
from texthumanize import async_humanize, async_detect_ai, analyze

app = FastAPI(
    title="TextHumanize API",
    version="1.0.0",
    description="Text humanization and AI detection",
)


class HumanizeRequest(BaseModel):
    text: str = Field(..., min_length=1, max_length=1_000_000)
    lang: str = Field("auto", pattern=r"^[a-z]{2}$|^auto$")
    profile: str = Field("web")
    intensity: int = Field(60, ge=0, le=100)
    seed: int | None = None


class DetectRequest(BaseModel):
    text: str = Field(..., min_length=1, max_length=1_000_000)
    lang: str = Field("auto", pattern=r"^[a-z]{2}$|^auto$")


class HumanizeResponse(BaseModel):
    text: str
    change_ratio: float
    quality_score: float
    lang: str


class DetectResponse(BaseModel):
    score: float
    verdict: str
    confidence: float


@app.post("/humanize", response_model=HumanizeResponse)
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
        return HumanizeResponse(
            text=result.text,
            change_ratio=result.change_ratio,
            quality_score=getattr(result, "quality_score", 0.0),
            lang=result.lang,
        )
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@app.post("/detect-ai", response_model=DetectResponse)
async def detect_ai_endpoint(req: DetectRequest):
    """Detect AI-generated text."""
    try:
        result = await async_detect_ai(req.text, lang=req.lang)
        return DetectResponse(
            score=result["score"],
            verdict=result["verdict"],
            confidence=result["confidence"],
        )
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@app.get("/health")
async def health():
    return {"status": "ok"}
```

## Run

```bash
uvicorn app:app --host 0.0.0.0 --port 8000
```

## With Middleware (Rate Limiting)

```python
from fastapi import Request
from fastapi.responses import JSONResponse
import time

# Simple in-memory rate limiter
_requests: dict[str, list[float]] = {}

@app.middleware("http")
async def rate_limit(request: Request, call_next):
    client_ip = request.client.host
    now = time.time()
    window = _requests.setdefault(client_ip, [])
    window[:] = [t for t in window if now - t < 60]  # 1-min window
    if len(window) >= 100:
        return JSONResponse({"error": "Rate limit exceeded"}, status_code=429)
    window.append(now)
    return await call_next(request)
```

## With Dependency Injection

```python
from functools import lru_cache
from texthumanize import Pipeline

@lru_cache()
def get_pipeline() -> Pipeline:
    """Singleton pipeline instance."""
    pipeline = Pipeline()
    # Register custom hooks if needed
    return pipeline

@app.post("/humanize-custom")
async def humanize_custom(
    req: HumanizeRequest,
    pipeline: Pipeline = Depends(get_pipeline),
):
    result = await async_humanize(
        req.text, lang=req.lang, profile=req.profile,
    )
    return {"text": result.text}
```
