# =============================================================================
# Stratum AI - Frontend Dockerfile (Railway deployment)
# =============================================================================

# Build stage - compile React/Vite app
FROM node:20-alpine AS build

WORKDIR /app

# Copy package files and install dependencies
COPY package*.json .npmrc ./
RUN npm ci --legacy-peer-deps

# Copy source
COPY . .

# Railway injects service variables as build args
# Vite needs VITE_* vars at build time (baked into the bundle)
ARG VITE_API_URL
ARG VITE_WS_URL
ARG VITE_DEFAULT_LOCALE
ENV VITE_API_URL=$VITE_API_URL
ENV VITE_WS_URL=$VITE_WS_URL
ENV VITE_DEFAULT_LOCALE=$VITE_DEFAULT_LOCALE

RUN echo "Building with VITE_API_URL=$VITE_API_URL" && npm run build

# Verify dist was created
RUN echo "=== Build output ===" && ls -la dist/ && echo "=== index.html ===" && head -5 dist/index.html

# Production stage - serve static files
FROM node:20-alpine

WORKDIR /app

# Install serve globally
RUN npm install -g serve@14

# Copy built assets from build stage
COPY --from=build /app/dist ./dist

# Verify files were copied
RUN echo "=== Production dist ===" && ls -la dist/ && du -sh dist/

# Railway sets PORT at runtime (typically 8080)
# serve -s enables SPA mode (all routes serve index.html)
CMD ["sh", "-c", "echo Starting serve on port ${PORT:-3000} && exec serve -s dist -l ${PORT:-3000}"]
