# =============================================================================
# Stratum AI - Backend Dockerfile (single-stage for Railway compatibility)
# =============================================================================
FROM python:3.14-slim-bookworm

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

# Set working directory and grant ownership to appuser
WORKDIR /app
RUN chown appuser:appgroup /app

# Install Python dependencies (this layer rebuilds when requirements change)
COPY requirements-prod.txt .
RUN pip install --no-cache-dir -r requirements-prod.txt

# Remove build dependencies to reduce image size (~200MB savings)
RUN apt-get purge -y --auto-remove build-essential libpq-dev \
    && rm -rf /var/lib/apt/lists/*

# Copy application code (.dockerignore excludes tests, cache, etc.)
COPY --chown=appuser:appgroup . .

# Ensure start.sh is executable
RUN chmod +x /app/start.sh

# Create directories for file uploads and ML data
RUN mkdir -p /app/ml_service/training_data /app/uploads /app/temp && \
    chown -R appuser:appgroup /app/ml_service /app/uploads /app/temp

# Switch to non-root user
USER appuser

# Expose port (Railway assigns dynamic PORT)
EXPOSE ${PORT:-8000}

# Health check - overridden by docker-compose when running locally
HEALTHCHECK --interval=30s --timeout=10s --retries=3 --start-period=40s \
  CMD curl -f http://localhost:${PORT:-8000}/health || exit 1

# Use start.sh entrypoint for proper shell variable expansion
ENTRYPOINT ["/app/start.sh"]
