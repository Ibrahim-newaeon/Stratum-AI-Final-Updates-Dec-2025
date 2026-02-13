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

# Production stage - use serve for Railway compatibility
FROM node:25-alpine AS production

WORKDIR /app

# Install serve - lightweight static file server
RUN npm install -g serve@14

# Copy built assets from build stage
COPY --from=build /app/dist ./dist

# serve -s enables SPA mode (all routes serve index.html)
# -l flag explicitly binds to PORT (Railway sets this at runtime)
CMD ["sh", "-c", "exec serve -s dist -l ${PORT:-3000}"]
