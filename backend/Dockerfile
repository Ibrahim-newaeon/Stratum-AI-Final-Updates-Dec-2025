# =============================================================================
# Stratum AI - Backend Dockerfile (multi-stage for fast builds)
# =============================================================================

# ---- Stage 1: Builder (compile native deps, then discard build tools) ----
FROM python:3.11-slim-bookworm AS builder

ENV PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

# Build tools only needed during pip install (not in final image)
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    libpq-dev \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /build
# deps-version: 3 — bump to force Railway cache invalidation
COPY requirements-prod.txt .
RUN pip install --prefix=/install --no-cache-dir -r requirements-prod.txt

# ---- Stage 2: Runtime (slim, no gcc/build-essential) ----
FROM python:3.11-slim-bookworm

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PYTHONPATH=/app \
    PIP_NO_CACHE_DIR=1

# Only runtime libraries (libpq5 for psycopg2, curl for healthcheck)
RUN apt-get update && apt-get install -y --no-install-recommends \
    libpq5 \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Create non-root user for security
RUN groupadd --gid 1000 appgroup && \
    useradd --uid 1000 --gid appgroup --shell /bin/bash --create-home appuser

# Set working directory
WORKDIR /app

# Copy installed Python packages from builder stage
COPY --from=builder /install /usr/local

# Copy application code (.dockerignore excludes tests, cache, etc.)
COPY --chown=appuser:appgroup . .

# Create directories for file uploads and ML data
RUN mkdir -p /app/ml_service/training_data /app/uploads /app/temp && \
    chown -R appuser:appgroup /app/ml_service /app/uploads /app/temp

# Switch to non-root user
USER appuser

# Expose port (Railway assigns dynamic PORT)
EXPOSE ${PORT:-8000}

# Health check (use /health/live — no DB/Redis dependency)
HEALTHCHECK --interval=30s --timeout=10s --start-period=60s --retries=3 \
    CMD curl -f http://localhost:${PORT:-8000}/health/live || exit 1

# Run migrations then start server (shell form to expand $PORT from Railway)
CMD ["sh", "-c", "python -m alembic upgrade head 2>&1 || echo 'Migration warning (non-fatal)'; uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-8000}"]
