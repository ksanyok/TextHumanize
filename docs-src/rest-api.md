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

OpenAPI 3.1 schema is available at `GET /openapi.json`.

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
| `GET`  | `/openapi.json` | OpenAPI 3.1 schema |
| `POST` | `/sse/humanize` | Server-Sent Events stream |

## Security & hardening

The server is **unauthenticated** and intended for local or trusted
deployment. Since v0.34.0 it ships secure defaults:

| Concern | Default | How to change |
|---------|---------|---------------|
| Bind address | `127.0.0.1` (loopback only) | `--host 0.0.0.0` to expose (prints a warning) |
| Remote AI backends (`backend`, `oss_api_url`, `openai_api_key`, `ollama_url`) | **Disabled** → HTTP `403` | `TEXTHUMANIZE_API_ALLOW_REMOTE_BACKENDS=1` |
| Outbound URL safety | SSRF-validated (loopback / private / cloud-metadata rejected → HTTP `400`) | — |
| Outbound response size | Capped at 10 MB | — |
| CORS origin | `*` | `TEXTHUMANIZE_API_CORS_ORIGIN=https://app.example.com` |

Why remote backends are gated: passing a URL that the server then fetches is a
Server-Side Request Forgery (SSRF) primitive. Keeping it off by default means an
anonymous caller cannot make your server reach internal services. When you do
enable it, every URL is still validated:

```bash
# Blocked by default (403):
curl -X POST http://127.0.0.1:8080/humanize \
  -H 'Content-Type: application/json' \
  -d '{"text":"hi","backend":"oss","oss_api_url":"http://169.254.169.254/"}'

# Enabled, but SSRF-validated — internal targets still 400:
TEXTHUMANIZE_API_ALLOW_REMOTE_BACKENDS=1 python -m texthumanize.api
```

Reuse the same guard in your own HTTP wrappers:

```python
from texthumanize import validate_outbound_url, UnsafeURLError

try:
    validate_outbound_url(user_supplied_url)   # raises on internal/loopback/metadata
except UnsafeURLError as exc:
    ...  # reject the request
```

For production, run behind a reverse proxy that adds TLS, authentication, and
request timeouts. See [SECURITY.md](https://github.com/ksanyok/TextHumanize/blob/main/SECURITY.md#rest-api-hardening-network-safety).

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
