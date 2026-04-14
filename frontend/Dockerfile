# =============================================================================
# Stratum AI - Frontend Dockerfile
# =============================================================================

# Development stage
FROM node:20-alpine AS development

WORKDIR /app

# Copy package files
COPY package*.json ./

# Install dependencies
RUN npm install

# Copy source code
COPY . .

# Expose Vite dev server port
EXPOSE 5173

# Start development server
CMD ["npm", "run", "dev", "--", "--host", "0.0.0.0"]

# =============================================================================
# Production build stage
# =============================================================================
FROM node:20-alpine AS build

WORKDIR /app

# VITE_API_URL must match what the frontend code reads via import.meta.env
ARG VITE_API_URL=https://api.stratumai.app/api/v1
ENV VITE_API_URL=$VITE_API_URL

COPY package*.json ./
RUN npm ci --legacy-peer-deps

COPY . .
RUN npm run build

# Production stage - Nginx serves static files
FROM nginx:alpine AS production

COPY --from=build /app/dist /usr/share/nginx/html
COPY nginx.conf /etc/nginx/templates/default.conf.template

# Railway assigns dynamic PORT; nginx:alpine uses envsubst on templates
ENV PORT=80

EXPOSE ${PORT}

CMD ["nginx", "-g", "daemon off;"]
