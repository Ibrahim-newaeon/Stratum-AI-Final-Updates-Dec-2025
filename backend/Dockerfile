# =============================================================================
# Stratum AI - Backend Dockerfile (single-stage for Railway compatibility)
# =============================================================================
FROM python:3.13-slim-bookworm

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PYTHONPATH=/app \
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

# Set working directory
WORKDIR /app

# Install Python dependencies (this layer rebuilds when requirements change)
COPY requirements-prod.txt .
RUN pip install --no-cache-dir -r requirements-prod.txt

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
