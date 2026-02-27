FROM python:3.12-slim AS base

LABEL maintainer="ksanyok@me.com"
LABEL org.opencontainers.image.title="TextHumanize"
LABEL org.opencontainers.image.description="Advanced text naturalization engine"
LABEL org.opencontainers.image.source="https://github.com/ksanyok/TextHumanize"

WORKDIR /app

# Copy only what's needed (no tests, no docs, no PHP/JS)
COPY pyproject.toml .
COPY texthumanize/ texthumanize/

RUN pip install --no-cache-dir -e . && \
    python -c "import texthumanize; print(f'TextHumanize {texthumanize.__version__} ready')"

# Non-root user for security
RUN useradd -m -r appuser && chown -R appuser:appuser /app
USER appuser

EXPOSE 8080

HEALTHCHECK --interval=30s --timeout=5s --retries=3 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:8080/health')" || exit 1

ENTRYPOINT ["python", "-m", "texthumanize"]
CMD ["--api", "--port", "8080"]
