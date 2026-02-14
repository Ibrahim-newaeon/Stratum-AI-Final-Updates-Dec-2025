# =============================================================================
# Stratum AI - Backend Dockerfile
# =============================================================================
FROM python:3.14-slim-bookworm

# Set environment variables
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PYTHONPATH=/app \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    libpq-dev \
    libxml2-dev \
    libxslt-dev \
    zlib1g-dev \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Create non-root user for security
RUN groupadd --gid 1000 appgroup && \
    useradd --uid 1000 --gid appgroup --shell /bin/bash --create-home appuser

# Set working directory
WORKDIR /app

# Copy requirements first for better caching
COPY requirements.txt .

# Install Python dependencies
RUN pip install --upgrade pip && \
    pip install -r requirements.txt

# Copy application code
COPY --chown=appuser:appgroup . .

# Create directories for file uploads and ML data
RUN mkdir -p /app/ml_service/training_data /app/uploads /app/temp && \
    chown -R appuser:appgroup /app/ml_service /app/uploads /app/temp

# Switch to non-root user
USER appuser

# Expose port (Railway sets PORT env var)
EXPOSE 8080

# Health check using liveness endpoint (no dependency checks)
HEALTHCHECK --interval=30s --timeout=10s --start-period=120s --retries=5 \
    CMD curl -f http://localhost:${PORT:-8080}/health/live || exit 1

# Default command - run migrations, seed admin, then start server
# Migrations use sync driver (psycopg2) and are idempotent (safe to run every deploy)
CMD ["sh", "-c", "echo '=== Running database migrations ===' && alembic upgrade head && echo '=== Migrations complete ===' && (python scripts/seed_superadmin.py || echo '=== Seed script skipped (non-fatal) ===') && echo '=== Starting server ===' && uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-8080}"]
