# =============================================================================
# Stratum AI - Backend Dockerfile (repo-root build context)
# -----------------------------------------------------------------------------
# Build context is the REPO ROOT, not backend/. This lets us copy both
# `backend/` and `docs/` into the image so the Copilot RAG indexer
# (`app.scripts.index_copilot_docs`) can resolve its curated corpus —
# the indexer computes REPO_ROOT as `Path(__file__).resolve().parents[3]`,
# which only points at a directory containing `docs/` when the in-container
# layout mirrors the repo layout.
#
# In-container layout:
#   /app/backend/...   (backend/ contents — app, alembic, scripts, start.sh)
#   /app/docs/...      (curated markdown corpus for Copilot RAG)
#
# WORKDIR is /app/backend so existing relative paths in start.sh
# (`python fix_alembic_version.py`, `python scripts/...`, `python -m alembic`)
# keep working unchanged.
# =============================================================================
FROM python:3.11-slim-bookworm

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PYTHONPATH=/app/backend \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

# Install build deps + runtime libs in one layer
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    libpq-dev \
    libpq5 \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Create non-root user for security
RUN groupadd --gid 1000 appgroup && \
    useradd --uid 1000 --gid appgroup --shell /bin/bash --create-home appuser

# Set working directory and grant ownership to appuser
WORKDIR /app/backend
RUN chown -R appuser:appgroup /app

# Install Python dependencies (this layer rebuilds when requirements change)
COPY backend/requirements-prod.txt .
RUN pip install --no-cache-dir -r requirements-prod.txt

# Remove build dependencies to reduce image size (~200MB savings)
RUN apt-get purge -y --auto-remove build-essential libpq-dev \
    && rm -rf /var/lib/apt/lists/*

# Copy backend application code (.dockerignore excludes tests, cache, etc.)
COPY --chown=appuser:appgroup backend/ /app/backend/

# Copy curated docs corpus for the Copilot RAG indexer
COPY --chown=appuser:appgroup docs/ /app/docs/

# Ensure start.sh is executable
RUN chmod +x /app/backend/start.sh

# Create directories for file uploads and ML data
RUN mkdir -p /app/backend/ml_service/training_data /app/backend/uploads /app/backend/temp && \
    chown -R appuser:appgroup /app/backend/ml_service /app/backend/uploads /app/backend/temp

# Pre-train ML models at build time so they're baked into the image.
# Runtime auto-train (in app/main.py) consumes ~9.5 GB and blocks /health
# from responding within Railway's healthcheck window. Doing it here makes
# every container start fast and idempotent.
ENV ML_MODELS_PATH=/app/backend/ml_service/models \
    APP_ENV=development
RUN python scripts/build_ml_models.py && \
    chown -R appuser:appgroup /app/backend/ml_service/models
# Re-set APP_ENV to production for runtime — build-time only needed dev
# defaults to avoid Pydantic validators tripping on missing prod secrets.
ENV APP_ENV=production

# Switch to non-root user
USER appuser

# Expose port (Railway assigns dynamic PORT)
EXPOSE ${PORT:-8000}

# Health check - overridden by docker-compose when running locally
HEALTHCHECK --interval=30s --timeout=10s --retries=3 --start-period=40s \
  CMD curl -f http://localhost:${PORT:-8000}/health || exit 1

# Use start.sh entrypoint for proper shell variable expansion
ENTRYPOINT ["/app/backend/start.sh"]
