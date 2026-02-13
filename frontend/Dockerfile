# =============================================================================
# Stratum AI - Frontend Dockerfile
# =============================================================================

# Development stage
FROM node:25-alpine AS development

WORKDIR /app

# Copy package files
COPY package*.json ./

# Install dependencies (use legacy-peer-deps for React 19 compatibility)
RUN npm install --legacy-peer-deps

# Copy source code
COPY . .

# Expose Vite dev server port
EXPOSE 5173

# Start development server
CMD ["npm", "run", "dev", "--", "--host", "0.0.0.0"]

# =============================================================================
# Production build stage
# =============================================================================
FROM node:25-alpine AS build

WORKDIR /app

COPY package*.json ./
RUN npm ci --legacy-peer-deps

COPY . .
RUN npm run build

# Production stage (memory audit Feb 2026)
FROM nginx:alpine AS production

# Copy built assets
COPY --from=build /app/dist /usr/share/nginx/html

# Use nginx template mechanism for dynamic PORT substitution
# The official nginx image auto-processes /etc/nginx/templates/*.template files
# with envsubst and outputs to /etc/nginx/conf.d/
COPY nginx.railway.conf /etc/nginx/templates/default.conf.template

# Remove the default config (template output will create default.conf)
RUN rm -f /etc/nginx/conf.d/default.conf

# Default PORT (Railway overrides this at runtime)
ENV PORT=80

EXPOSE 80

HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD wget -q --spider http://localhost:${PORT}/health || exit 1

CMD ["nginx", "-g", "daemon off;"]

# Result: ~25MB container vs ~500MB with Vite dev server (per memory audit)
