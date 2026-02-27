# REST API

TextHumanize includes a zero-dependency HTTP server built on Python stdlib.

## Start Server

```bash
python -m texthumanize.api --port 8080
# or
texthumanize dummy --api --port 8080
# or via Docker
docker run -p 8080:8080 texthumanize
```

## Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| `POST` | `/humanize` | Humanize text |
| `POST` | `/detect-ai` | AI detection |
| `POST` | `/analyze` | Text metrics |
| `POST` | `/paraphrase` | Paraphrase |
| `POST` | `/tone/analyze` | Tone analysis |
| `POST` | `/tone/adjust` | Tone adjustment |
| `POST` | `/watermarks/detect` | Detect watermarks |
| `POST` | `/watermarks/clean` | Clean watermarks |
| `POST` | `/spin` | Text spinning |
| `POST` | `/spin/variants` | Spin variants |
| `POST` | `/coherence` | Coherence analysis |
| `POST` | `/readability` | Readability metrics |
| `GET`  | `/health` | Health check |
| `GET`  | `/sse/humanize` | Server-Sent Events stream |

## Examples

### Humanize

```bash
curl -X POST http://localhost:8080/humanize \
  -H "Content-Type: application/json" \
  -d '{
    "text": "Furthermore, it is important to note that this approach facilitates optimization.",
    "lang": "en",
    "profile": "web",
    "intensity": 70
  }'
```

Response:
```json
{
  "text": "But this approach helps with optimization.",
  "change_ratio": 0.15,
  "quality_score": 0.85,
  "lang": "en",
  "_elapsed_ms": 142.3
}
```

### AI Detection

```bash
curl -X POST http://localhost:8080/detect-ai \
  -H "Content-Type: application/json" \
  -d '{"text": "Text to check.", "lang": "en"}'
```

### SSE Streaming

```bash
curl -N "http://localhost:8080/sse/humanize" \
  -H "Content-Type: application/json" \
  -d '{"text": "Long text...", "lang": "en"}'
```

Response (SSE format):
```
data: {"chunk": "First paragraph...", "index": 0}

data: {"chunk": "Second paragraph...", "index": 1}

data: {"done": true, "total_chunks": 2}
```

### Health Check

```bash
curl http://localhost:8080/health
```

```json
{
  "status": "ok",
  "version": "0.16.0",
  "endpoints": ["/analyze", "/coherence", "/detect-ai", ...]
}
```
