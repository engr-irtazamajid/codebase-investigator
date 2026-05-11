# ── Builder ────────────────────────────────────────────────────────────────────
FROM python:3.12-slim AS builder

WORKDIR /app

# git is needed at runtime (repo cloning), install in builder to cache the layer
RUN apt-get update && apt-get install -y --no-install-recommends git \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir --upgrade pip \
    && pip install --no-cache-dir -r requirements.txt

# ── Runtime ────────────────────────────────────────────────────────────────────
FROM python:3.12-slim AS runtime

WORKDIR /app

# Non-root user for security
RUN addgroup --system app && adduser --system --ingroup app app

# Copy git binary and shared libs from builder
COPY --from=builder /usr/bin/git /usr/bin/git
COPY --from=builder /usr/lib /usr/lib

# Copy installed Python packages
COPY --from=builder /usr/local/lib/python3.12/site-packages /usr/local/lib/python3.12/site-packages
COPY --from=builder /usr/local/bin /usr/local/bin

# Copy application code
COPY app/ ./app/

RUN chown -R app:app /app
USER app

EXPOSE 8000

# Use /tmp for cloned repos (writable by non-root)
ENV TMPDIR=/tmp

HEALTHCHECK --interval=30s --timeout=5s --start-period=15s --retries=3 \
    CMD sh -c "python -c \"import urllib.request; urllib.request.urlopen('http://localhost:${PORT:-8000}/health')\""

# Shell form so $PORT is expanded at runtime (exec form does not expand env vars)
CMD ["sh", "-c", "uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-8000} --workers 2 --no-access-log"]
