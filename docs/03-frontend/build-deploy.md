# Build & Deployment

## Overview

Stratum AI frontend is built with Vite and deployed as a static SPA.

---

## Development

### Start Dev Server

```bash
cd frontend
npm install
npm run dev
```

The dev server runs at `http://localhost:5173` with:
- Hot Module Replacement (HMR)
- Fast refresh
- TypeScript error overlay

### Environment Variables

Create `.env` file:

```env
VITE_API_BASE_URL=http://localhost:8000
VITE_WS_URL=ws://localhost:8000
VITE_DEFAULT_LOCALE=en
VITE_SENTRY_DSN=
```

**Note:** Only variables prefixed with `VITE_` are exposed to the frontend.

---

## Build

### Production Build

```bash
npm run build
```

Output in `dist/`:
```
dist/
├── index.html
├── assets/
│   ├── index-[hash].js
│   ├── index-[hash].css
│   └── vendor-[hash].js
└── favicon.ico
```

### Preview Production Build

```bash
npm run preview
```

Serves the built files at `http://localhost:4173`.

---

## Vite Configuration

```ts
// vite.config.ts
import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'
import path from 'path'

export default defineConfig({
  plugins: [react()],

  resolve: {
    alias: {
      '@': path.resolve(__dirname, './src'),
    },
  },

  server: {
    port: 5173,
    proxy: {
      '/api': {
        target: 'http://localhost:8000',
        changeOrigin: true,
      },
      '/ws': {
        target: 'ws://localhost:8000',
        ws: true,
      },
    },
  },

  build: {
    outDir: 'dist',
    sourcemap: true,
    rollupOptions: {
      output: {
        manualChunks: {
          'react-vendor': ['react', 'react-dom', 'react-router-dom'],
          'chart-vendor': ['recharts', '@tremor/react'],
        },
      },
    },
  },
})
```

---

## Docker

### Dockerfile

```dockerfile
# frontend/Dockerfile

# Build stage
FROM node:20-alpine AS builder
WORKDIR /app

COPY package*.json ./
RUN npm ci

COPY . .
RUN npm run build

# Production stage
FROM nginx:alpine AS production
COPY --from=builder /app/dist /usr/share/nginx/html
COPY nginx.conf /etc/nginx/nginx.conf
EXPOSE 80
CMD ["nginx", "-g", "daemon off;"]

# Development stage
FROM node:20-alpine AS development
WORKDIR /app
COPY package*.json ./
RUN npm install
COPY . .
EXPOSE 5173
CMD ["npm", "run", "dev", "--", "--host", "0.0.0.0"]
```

### Nginx Configuration

```nginx
# nginx.conf
server {
    listen 80;
    server_name localhost;
    root /usr/share/nginx/html;
    index index.html;

    # Gzip compression
    gzip on;
    gzip_types text/plain text/css application/json application/javascript;

    # Cache static assets
    location /assets/ {
        expires 1y;
        add_header Cache-Control "public, immutable";
    }

    # SPA fallback
    location / {
        try_files $uri $uri/ /index.html;
    }

    # API proxy (if needed)
    location /api/ {
        proxy_pass http://api:8000;
        proxy_http_version 1.1;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
    }
}
```

---

## Deployment Environments

### Development

```env
VITE_API_BASE_URL=http://localhost:8000
VITE_WS_URL=ws://localhost:8000
```

### Staging

```env
VITE_API_BASE_URL=https://api.staging.stratum.ai
VITE_WS_URL=wss://api.staging.stratum.ai
VITE_SENTRY_DSN=https://xxx@sentry.io/staging
```

### Production

```env
VITE_API_BASE_URL=https://api.stratum.ai
VITE_WS_URL=wss://api.stratum.ai
VITE_SENTRY_DSN=https://xxx@sentry.io/production
```

---

## AWS Deployment

### S3 + CloudFront

```yaml
# Infrastructure (Terraform/CloudFormation)

# S3 Bucket
resource "aws_s3_bucket" "frontend" {
  bucket = "stratum-frontend"
}

resource "aws_s3_bucket_website_configuration" "frontend" {
  bucket = aws_s3_bucket.frontend.id
  index_document { suffix = "index.html" }
  error_document { key = "index.html" }  # SPA fallback
}

# CloudFront Distribution
resource "aws_cloudfront_distribution" "frontend" {
  origin {
    domain_name = aws_s3_bucket.frontend.bucket_regional_domain_name
    origin_id   = "S3-frontend"
  }

  default_cache_behavior {
    viewer_protocol_policy = "redirect-to-https"
    allowed_methods        = ["GET", "HEAD"]
    cached_methods         = ["GET", "HEAD"]
    target_origin_id       = "S3-frontend"

    forwarded_values {
      query_string = false
      cookies { forward = "none" }
    }
  }

  # SPA error handling
  custom_error_response {
    error_code         = 404
    response_code      = 200
    response_page_path = "/index.html"
  }
}
```

### Deployment Script

```bash
#!/bin/bash
# deploy.sh

# Build
npm run build

# Sync to S3
aws s3 sync dist/ s3://stratum-frontend --delete

# Invalidate CloudFront cache
aws cloudfront create-invalidation \
  --distribution-id $CF_DISTRIBUTION_ID \
  --paths "/*"
```

---

## CI/CD Pipeline

### GitHub Actions

```yaml
# .github/workflows/deploy-frontend.yml
name: Deploy Frontend

on:
  push:
    branches: [main]
    paths:
      - 'frontend/**'

jobs:
  build-and-deploy:
    runs-on: ubuntu-latest

    steps:
      - uses: actions/checkout@v4

      - name: Setup Node
        uses: actions/setup-node@v4
        with:
          node-version: '20'
          cache: 'npm'
          cache-dependency-path: frontend/package-lock.json

      - name: Install dependencies
        working-directory: frontend
        run: npm ci

      - name: Run tests
        working-directory: frontend
        run: npm run test

      - name: Build
        working-directory: frontend
        run: npm run build
        env:
          VITE_API_BASE_URL: ${{ secrets.VITE_API_BASE_URL }}
          VITE_SENTRY_DSN: ${{ secrets.VITE_SENTRY_DSN }}

      - name: Deploy to S3
        uses: aws-actions/configure-aws-credentials@v4
        with:
          aws-access-key-id: ${{ secrets.AWS_ACCESS_KEY_ID }}
          aws-secret-access-key: ${{ secrets.AWS_SECRET_ACCESS_KEY }}
          aws-region: us-east-1

      - name: Sync to S3
        run: aws s3 sync frontend/dist s3://${{ secrets.S3_BUCKET }} --delete

      - name: Invalidate CloudFront
        run: |
          aws cloudfront create-invalidation \
            --distribution-id ${{ secrets.CF_DISTRIBUTION_ID }} \
            --paths "/*"
```

---

## Environment-Specific Builds

### Build with Environment

```bash
# Development
npm run build -- --mode development

# Staging
npm run build -- --mode staging

# Production
npm run build -- --mode production
```

### Environment Files

```
.env                # Default
.env.local          # Local overrides (git ignored)
.env.development    # Development mode
.env.staging        # Staging mode
.env.production     # Production mode
```

---

## Build Optimization

### Analyze Bundle

```bash
# Install analyzer
npm install -D rollup-plugin-visualizer

# Add to vite.config.ts
import { visualizer } from 'rollup-plugin-visualizer'

plugins: [
  visualizer({
    open: true,
    filename: 'stats.html',
  }),
]
```

### Chunk Strategy

```ts
// vite.config.ts
build: {
  rollupOptions: {
    output: {
      manualChunks: (id) => {
        if (id.includes('node_modules')) {
          if (id.includes('react')) return 'react-vendor'
          if (id.includes('recharts')) return 'chart-vendor'
          if (id.includes('@radix-ui')) return 'ui-vendor'
          return 'vendor'
        }
      },
    },
  },
}
```

---

## Health Checks

### Frontend Health

The frontend serves `index.html` for all routes (SPA). Health can be verified by:

```bash
# Check if frontend is serving
curl -I https://app.stratum.ai

# Expected: HTTP 200
```

### CloudFront Health

```bash
# Check CloudFront distribution
aws cloudfront get-distribution --id $DISTRIBUTION_ID
```

---

## Rollback

### Quick Rollback

```bash
# S3 versioning enabled
aws s3api list-object-versions \
  --bucket stratum-frontend \
  --prefix index.html

# Restore previous version
aws s3api copy-object \
  --bucket stratum-frontend \
  --copy-source stratum-frontend/index.html?versionId=$PREV_VERSION \
  --key index.html
```

### Full Rollback

```bash
# Redeploy previous build
git checkout $PREVIOUS_TAG
cd frontend
npm ci
npm run build
aws s3 sync dist/ s3://stratum-frontend --delete
```
