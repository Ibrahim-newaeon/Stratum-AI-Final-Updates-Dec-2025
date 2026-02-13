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

# Debug: verify public files exist before build
RUN echo "=== public/ before build ===" && ls -la public/ && echo "=== public/landing.html exists ===" && wc -c public/landing.html

# Railway injects service variables as build args
# Vite needs VITE_* vars at build time (baked into the bundle)
ARG VITE_API_URL
ARG VITE_WS_URL
ARG VITE_DEFAULT_LOCALE
ENV VITE_API_URL=$VITE_API_URL
ENV VITE_WS_URL=$VITE_WS_URL
ENV VITE_DEFAULT_LOCALE=$VITE_DEFAULT_LOCALE

RUN echo "Building with VITE_API_URL=$VITE_API_URL" && npm run build

# Debug: check what Vite produced
RUN echo "=== dist/ after build ===" && ls -la dist/ && \
    echo "=== dist/assets/ ===" && ls -la dist/assets/ 2>/dev/null || true && \
    echo "=== landing.html in dist? ===" && (test -f dist/landing.html && echo "YES - found" || echo "NO - missing")

# Fallback: if Vite didn't copy public files, do it manually
RUN if [ ! -f dist/landing.html ]; then \
      echo ">>> Manually copying public/ to dist/" && \
      cp -r public/* dist/; \
    fi

# Final verification
RUN echo "=== Final dist/ contents ===" && find dist/ -type f | head -50 && \
    echo "=== dist/ size ===" && du -sh dist/

# Production stage - serve static files
FROM node:20-alpine

WORKDIR /app

# Install serve globally
RUN npm install -g serve@14

# Copy built assets from build stage
COPY --from=build /app/dist ./dist

# Verify files were copied
RUN echo "=== Production dist ===" && ls -la dist/ && \
    echo "=== landing.html ===" && (test -f dist/landing.html && echo "FOUND" || echo "MISSING") && \
    du -sh dist/

# Disable serve's "clean URLs" feature which strips .html extensions
# (redirects /landing.html → /landing which breaks iframe loading)
RUN echo '{"cleanUrls": false}' > dist/serve.json

# Railway sets PORT at runtime (typically 8080)
# serve -s enables SPA mode (all routes serve index.html)
CMD ["sh", "-c", "exec serve -s dist -l ${PORT:-3000}"]
