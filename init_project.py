#!/usr/bin/env python3
"""
Stratum AI - Project Initialization Script
==========================================

This script creates the entire Stratum AI project structure when executed.
It generates all directories, configuration files, and source code.

Usage:
    python init_project.py [--target-dir /path/to/project]

Requirements:
    - Python 3.11+
    - No external dependencies (uses stdlib only)
"""

import os
import sys
import argparse
import textwrap
from pathlib import Path
from typing import Dict, Any

# =============================================================================
# Project Configuration
# =============================================================================

PROJECT_NAME = "stratum-ai"
PROJECT_DESCRIPTION = "Enterprise Marketing SaaS Platform with AI Intelligence"

# Directory structure
DIRECTORIES = [
    # Root directories
    "backend",
    "frontend",

    # Backend structure
    "backend/app",
    "backend/app/api",
    "backend/app/api/v1",
    "backend/app/api/v1/endpoints",
    "backend/app/core",
    "backend/app/db",
    "backend/app/middleware",
    "backend/app/ml",
    "backend/app/services",
    "backend/app/workers",
    "backend/migrations",
    "backend/migrations/versions",
    "backend/tests",
    "backend/tests/unit",
    "backend/tests/integration",

    # Frontend structure
    "frontend/src",
    "frontend/src/components",
    "frontend/src/components/common",
    "frontend/src/components/guide",
    "frontend/src/components/widgets",
    "frontend/src/components/ui",
    "frontend/src/hooks",
    "frontend/src/lib",
    "frontend/src/services",
    "frontend/src/views",
    "frontend/src/i18n",
    "frontend/src/i18n/locales",
    "frontend/src/i18n/locales/en",
    "frontend/src/i18n/locales/uk",
    "frontend/public",
]


# =============================================================================
# File Contents
# =============================================================================

FILES: Dict[str, str] = {}

# -----------------------------------------------------------------------------
# Root Configuration Files
# -----------------------------------------------------------------------------

FILES[".env.example"] = '''# =============================================================================
# Stratum AI - Environment Configuration
# =============================================================================

# Application
APP_NAME=Stratum AI
APP_ENV=development
DEBUG=true
SECRET_KEY=your-secret-key-change-in-production

# Database
DATABASE_URL=postgresql+asyncpg://stratum:stratum@db:5432/stratum
DATABASE_SYNC_URL=postgresql://stratum:stratum@db:5432/stratum

# Redis
REDIS_URL=redis://redis:6379/0
CELERY_BROKER_URL=redis://redis:6379/1
CELERY_RESULT_BACKEND=redis://redis:6379/2

# JWT Configuration
JWT_SECRET_KEY=your-jwt-secret-key
JWT_ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=30
REFRESH_TOKEN_EXPIRE_DAYS=7

# PII Encryption
PII_ENCRYPTION_KEY=your-32-byte-encryption-key-here

# API Keys (Optional - for production integrations)
GOOGLE_ADS_CLIENT_ID=
GOOGLE_ADS_CLIENT_SECRET=
META_ADS_ACCESS_TOKEN=
SERPAPI_KEY=
DATAFORSEO_LOGIN=
DATAFORSEO_PASSWORD=

# ML Configuration
ML_PROVIDER=local
VERTEX_AI_PROJECT=
VERTEX_AI_LOCATION=us-central1

# Logging
LOG_LEVEL=INFO
LOG_FORMAT=console

# CORS
CORS_ORIGINS=["http://localhost:3000","http://localhost:5173"]

# Rate Limiting
RATE_LIMIT_REQUESTS=100
RATE_LIMIT_WINDOW=60
'''

FILES[".gitignore"] = '''# Python
__pycache__/
*.py[cod]
*$py.class
*.so
.Python
build/
develop-eggs/
dist/
downloads/
eggs/
.eggs/
lib/
lib64/
parts/
sdist/
var/
wheels/
*.egg-info/
.installed.cfg
*.egg

# Virtual environments
.venv/
venv/
ENV/

# IDE
.idea/
.vscode/
*.swp
*.swo
*~

# Environment
.env
.env.local
.env.*.local

# Logs
*.log
logs/

# Testing
.coverage
htmlcov/
.pytest_cache/
.tox/

# Node
node_modules/
npm-debug.log*
yarn-debug.log*
yarn-error.log*

# Build
dist/
build/

# OS
.DS_Store
Thumbs.db

# Secrets
*.pem
*.key
secrets/

# Database
*.db
*.sqlite3
'''

FILES["docker-compose.yml"] = '''version: "3.9"

services:
  db:
    image: postgres:16-alpine
    container_name: stratum-db
    environment:
      POSTGRES_USER: stratum
      POSTGRES_PASSWORD: stratum
      POSTGRES_DB: stratum
    volumes:
      - postgres_data:/var/lib/postgresql/data
    ports:
      - "5432:5432"
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U stratum"]
      interval: 10s
      timeout: 5s
      retries: 5
    restart: unless-stopped

  redis:
    image: redis:7-alpine
    container_name: stratum-redis
    command: redis-server --appendonly yes
    volumes:
      - redis_data:/data
    ports:
      - "6379:6379"
    healthcheck:
      test: ["CMD", "redis-cli", "ping"]
      interval: 10s
      timeout: 5s
      retries: 5
    restart: unless-stopped

  api:
    build:
      context: ./backend
      dockerfile: Dockerfile
    container_name: stratum-api
    command: uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
    volumes:
      - ./backend:/app
    ports:
      - "8000:8000"
    environment:
      - DATABASE_URL=postgresql+asyncpg://stratum:stratum@db:5432/stratum
      - DATABASE_SYNC_URL=postgresql://stratum:stratum@db:5432/stratum
      - REDIS_URL=redis://redis:6379/0
      - CELERY_BROKER_URL=redis://redis:6379/1
    depends_on:
      db:
        condition: service_healthy
      redis:
        condition: service_healthy
    restart: unless-stopped

  worker:
    build:
      context: ./backend
      dockerfile: Dockerfile
    container_name: stratum-worker
    command: celery -A app.workers.celery_app worker --loglevel=info
    volumes:
      - ./backend:/app
    environment:
      - DATABASE_URL=postgresql+asyncpg://stratum:stratum@db:5432/stratum
      - DATABASE_SYNC_URL=postgresql://stratum:stratum@db:5432/stratum
      - CELERY_BROKER_URL=redis://redis:6379/1
      - CELERY_RESULT_BACKEND=redis://redis:6379/2
    depends_on:
      - api
      - redis
    restart: unless-stopped

  scheduler:
    build:
      context: ./backend
      dockerfile: Dockerfile
    container_name: stratum-scheduler
    command: celery -A app.workers.celery_app beat --loglevel=info
    volumes:
      - ./backend:/app
    environment:
      - DATABASE_URL=postgresql+asyncpg://stratum:stratum@db:5432/stratum
      - DATABASE_SYNC_URL=postgresql://stratum:stratum@db:5432/stratum
      - CELERY_BROKER_URL=redis://redis:6379/1
      - CELERY_RESULT_BACKEND=redis://redis:6379/2
    depends_on:
      - worker
    restart: unless-stopped

  flower:
    build:
      context: ./backend
      dockerfile: Dockerfile
    container_name: stratum-flower
    command: celery -A app.workers.celery_app flower --port=5555
    ports:
      - "5555:5555"
    environment:
      - CELERY_BROKER_URL=redis://redis:6379/1
      - CELERY_RESULT_BACKEND=redis://redis:6379/2
    depends_on:
      - worker
    restart: unless-stopped

  frontend:
    build:
      context: ./frontend
      dockerfile: Dockerfile
    container_name: stratum-frontend
    command: npm run dev -- --host 0.0.0.0
    volumes:
      - ./frontend:/app
      - /app/node_modules
    ports:
      - "5173:5173"
    environment:
      - VITE_API_URL=http://localhost:8000/api/v1
    depends_on:
      - api
    restart: unless-stopped

volumes:
  postgres_data:
  redis_data:
'''

FILES["README.md"] = '''# Stratum AI

Enterprise Marketing SaaS Platform with AI Intelligence

## Quick Start

1. **Prerequisites**
   - Docker & Docker Compose
   - Node.js 18+ (for local frontend development)
   - Python 3.11+ (for local backend development)

2. **Setup**
   ```bash
   # Copy environment file
   cp .env.example .env

   # Start all services
   docker-compose up -d

   # Run database migrations
   docker-compose exec api alembic upgrade head

   # Generate sample data
   docker-compose exec api python -m app.scripts.seed_data
   ```

3. **Access**
   - Frontend: http://localhost:5173
   - API: http://localhost:8000
   - API Docs: http://localhost:8000/docs
   - Flower (Celery): http://localhost:5555

## Architecture

```
stratum-ai/
├── backend/              # FastAPI Backend
│   ├── app/
│   │   ├── api/         # REST endpoints
│   │   ├── core/        # Config, security
│   │   ├── db/          # Database sessions
│   │   ├── middleware/  # Custom middleware
│   │   ├── ml/          # ML/AI modules
│   │   ├── models.py    # SQLAlchemy models
│   │   ├── schemas.py   # Pydantic schemas
│   │   ├── services/    # Business logic
│   │   └── workers/     # Celery tasks
│   └── migrations/      # Alembic migrations
├── frontend/            # React Frontend
│   └── src/
│       ├── components/  # UI components
│       ├── views/       # Page views
│       ├── services/    # API client
│       └── i18n/        # Translations
└── docker-compose.yml
```

## Modules

- **Module A**: Intelligence Engine (ML/AI)
- **Module B**: Data Integration & DAM
- **Module C**: Stratum Automation (Rules Engine)
- **Module D**: Competitor Intelligence
- **Module E**: Stratum Guide (Onboarding)
- **Module F**: Security & Governance
- **Module G**: Dashboard

## License

Proprietary - All Rights Reserved
'''

# -----------------------------------------------------------------------------
# Backend Files
# -----------------------------------------------------------------------------

FILES["backend/Dockerfile"] = '''FROM python:3.11-slim

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \\
    build-essential \\
    libpq-dev \\
    && rm -rf /var/lib/apt/lists/*

# Install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY . .

# Create non-root user
RUN useradd -m -u 1000 stratum && chown -R stratum:stratum /app
USER stratum

EXPOSE 8000

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
'''

FILES["backend/requirements.txt"] = '''# FastAPI & Server
fastapi>=0.104.0
uvicorn[standard]>=0.24.0
python-multipart>=0.0.6
python-jose[cryptography]>=3.3.0
passlib[bcrypt]>=1.7.4
httpx>=0.25.0

# Database
sqlalchemy[asyncio]>=2.0.0
asyncpg>=0.29.0
psycopg2-binary>=2.9.9
alembic>=1.12.0
greenlet>=3.0.0

# Redis & Celery
redis>=5.0.0
celery[redis]>=5.3.0
flower>=2.0.0

# Validation & Serialization
pydantic>=2.5.0
pydantic-settings>=2.1.0
email-validator>=2.1.0

# ML & Data
numpy>=1.26.0
pandas>=2.1.0
scikit-learn>=1.3.0

# Logging & Monitoring
structlog>=23.2.0
sentry-sdk[fastapi]>=1.35.0

# Utilities
python-dotenv>=1.0.0
cryptography>=41.0.0
beautifulsoup4>=4.12.0
lxml>=4.9.0

# Testing
pytest>=7.4.0
pytest-asyncio>=0.21.0
pytest-cov>=4.1.0
httpx>=0.25.0
factory-boy>=3.3.0
'''

FILES["backend/alembic.ini"] = '''[alembic]
script_location = migrations
prepend_sys_path = .
sqlalchemy.url = driver://user:pass@localhost/dbname

[post_write_hooks]

[loggers]
keys = root,sqlalchemy,alembic

[handlers]
keys = console

[formatters]
keys = generic

[logger_root]
level = WARN
handlers = console
qualname =

[logger_sqlalchemy]
level = WARN
handlers =
qualname = sqlalchemy.engine

[logger_alembic]
level = INFO
handlers =
qualname = alembic

[handler_console]
class = StreamHandler
args = (sys.stderr,)
level = NOTSET
formatter = generic

[formatter_generic]
format = %(levelname)-5.5s [%(name)s] %(message)s
datefmt = %H:%M:%S
'''

FILES["backend/app/__init__.py"] = '''"""Stratum AI Backend Application."""
__version__ = "1.0.0"
'''

FILES["backend/app/core/__init__.py"] = '''"""Core module initialization."""
'''

FILES["backend/app/core/config.py"] = '''"""Application configuration using Pydantic Settings."""
from functools import lru_cache
from typing import List, Optional
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
    )

    # Application
    app_name: str = "Stratum AI"
    app_env: str = "development"
    debug: bool = True
    secret_key: str = "change-me-in-production"

    # Database
    database_url: str = "postgresql+asyncpg://stratum:stratum@localhost:5432/stratum"
    database_sync_url: str = "postgresql://stratum:stratum@localhost:5432/stratum"

    # Redis
    redis_url: str = "redis://localhost:6379/0"
    celery_broker_url: str = "redis://localhost:6379/1"
    celery_result_backend: str = "redis://localhost:6379/2"

    # JWT
    jwt_secret_key: str = "jwt-secret-change-in-production"
    jwt_algorithm: str = "HS256"
    access_token_expire_minutes: int = 30
    refresh_token_expire_days: int = 7

    # PII Encryption
    pii_encryption_key: str = "32-byte-encryption-key-here-now"

    # ML Configuration
    ml_provider: str = "local"
    vertex_ai_project: Optional[str] = None
    vertex_ai_location: str = "us-central1"

    # Logging
    log_level: str = "INFO"
    log_format: str = "console"

    # CORS
    cors_origins: List[str] = ["http://localhost:3000", "http://localhost:5173"]

    # Rate Limiting
    rate_limit_requests: int = 100
    rate_limit_window: int = 60

    @property
    def is_production(self) -> bool:
        return self.app_env == "production"


@lru_cache()
def get_settings() -> Settings:
    """Get cached settings instance."""
    return Settings()


settings = get_settings()
'''

FILES["backend/app/api/__init__.py"] = '''"""API module initialization."""
'''

FILES["backend/app/api/v1/__init__.py"] = '''"""API v1 router aggregation."""
from fastapi import APIRouter

from app.api.v1.endpoints import auth, users, campaigns, assets, rules, analytics, simulator, competitors, gdpr

api_router = APIRouter()

api_router.include_router(auth.router, prefix="/auth", tags=["Authentication"])
api_router.include_router(users.router, prefix="/users", tags=["Users"])
api_router.include_router(campaigns.router, prefix="/campaigns", tags=["Campaigns"])
api_router.include_router(assets.router, prefix="/assets", tags=["Assets"])
api_router.include_router(rules.router, prefix="/rules", tags=["Rules"])
api_router.include_router(analytics.router, prefix="/analytics", tags=["Analytics"])
api_router.include_router(simulator.router, prefix="/simulator", tags=["Simulator"])
api_router.include_router(competitors.router, prefix="/competitors", tags=["Competitors"])
api_router.include_router(gdpr.router, prefix="/gdpr", tags=["GDPR"])
'''

FILES["backend/app/api/v1/endpoints/__init__.py"] = '''"""API endpoints initialization."""
'''

FILES["backend/app/db/__init__.py"] = '''"""Database module initialization."""
'''

FILES["backend/app/middleware/__init__.py"] = '''"""Middleware module initialization."""
'''

FILES["backend/app/ml/__init__.py"] = '''"""ML module initialization."""
'''

FILES["backend/app/services/__init__.py"] = '''"""Services module initialization."""
'''

FILES["backend/app/workers/__init__.py"] = '''"""Workers module initialization."""
'''

FILES["backend/migrations/env.py"] = '''"""Alembic migration environment configuration."""
import asyncio
from logging.config import fileConfig
from sqlalchemy import pool
from sqlalchemy.engine import Connection
from sqlalchemy.ext.asyncio import async_engine_from_config
from alembic import context

from app.core.config import settings
from app.models import Base

config = context.config
config.set_main_option("sqlalchemy.url", settings.database_sync_url)

if config.config_file_name is not None:
    fileConfig(config.config_file_name)

target_metadata = Base.metadata


def run_migrations_offline() -> None:
    """Run migrations in offline mode."""
    url = config.get_main_option("sqlalchemy.url")
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )

    with context.begin_transaction():
        context.run_migrations()


def do_run_migrations(connection: Connection) -> None:
    context.configure(connection=connection, target_metadata=target_metadata)

    with context.begin_transaction():
        context.run_migrations()


async def run_async_migrations() -> None:
    """Run migrations in async mode."""
    connectable = async_engine_from_config(
        config.get_section(config.config_ini_section, {}),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )

    async with connectable.connect() as connection:
        await connection.run_sync(do_run_migrations)

    await connectable.dispose()


def run_migrations_online() -> None:
    """Run migrations in online mode."""
    asyncio.run(run_async_migrations())


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
'''

FILES["backend/migrations/script.py.mako"] = '''"""${message}

Revision ID: ${up_revision}
Revises: ${down_revision | comma,n}
Create Date: ${create_date}

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
${imports if imports else ""}

# revision identifiers, used by Alembic.
revision: str = ${repr(up_revision)}
down_revision: Union[str, None] = ${repr(down_revision)}
branch_labels: Union[str, Sequence[str], None] = ${repr(branch_labels)}
depends_on: Union[str, Sequence[str], None] = ${repr(depends_on)}


def upgrade() -> None:
    ${upgrades if upgrades else "pass"}


def downgrade() -> None:
    ${downgrades if downgrades else "pass"}
'''

FILES["backend/tests/__init__.py"] = '''"""Tests module initialization."""
'''

# -----------------------------------------------------------------------------
# Frontend Files
# -----------------------------------------------------------------------------

FILES["frontend/Dockerfile"] = '''FROM node:18-alpine

WORKDIR /app

# Install dependencies
COPY package*.json ./
RUN npm ci

# Copy source code
COPY . .

EXPOSE 5173

CMD ["npm", "run", "dev", "--", "--host", "0.0.0.0"]
'''

FILES["frontend/package.json"] = '''{
  "name": "stratum-ai-frontend",
  "private": true,
  "version": "1.0.0",
  "type": "module",
  "scripts": {
    "dev": "vite",
    "build": "tsc && vite build",
    "lint": "eslint . --ext ts,tsx --report-unused-disable-directives --max-warnings 0",
    "preview": "vite preview"
  },
  "dependencies": {
    "@tanstack/react-query": "^5.8.0",
    "axios": "^1.6.0",
    "clsx": "^2.0.0",
    "i18next": "^23.7.0",
    "lucide-react": "^0.292.0",
    "react": "^18.2.0",
    "react-dom": "^18.2.0",
    "react-i18next": "^13.5.0",
    "react-joyride": "^2.7.0",
    "react-router-dom": "^6.20.0",
    "recharts": "^2.10.0",
    "tailwind-merge": "^2.0.0",
    "zustand": "^4.4.0"
  },
  "devDependencies": {
    "@types/react": "^18.2.0",
    "@types/react-dom": "^18.2.0",
    "@typescript-eslint/eslint-plugin": "^6.10.0",
    "@typescript-eslint/parser": "^6.10.0",
    "@vitejs/plugin-react": "^4.2.0",
    "autoprefixer": "^10.4.0",
    "eslint": "^8.53.0",
    "eslint-plugin-react-hooks": "^4.6.0",
    "eslint-plugin-react-refresh": "^0.4.0",
    "postcss": "^8.4.0",
    "tailwindcss": "^3.3.0",
    "typescript": "^5.2.0",
    "vite": "^5.0.0"
  }
}
'''

FILES["frontend/vite.config.ts"] = '''import { defineConfig } from 'vite'
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
    host: true,
  },
})
'''

FILES["frontend/tailwind.config.js"] = '''/** @type {import('tailwindcss').Config} */
export default {
  darkMode: ['class'],
  content: [
    './index.html',
    './src/**/*.{js,ts,jsx,tsx}',
  ],
  theme: {
    extend: {
      colors: {
        border: 'hsl(var(--border))',
        input: 'hsl(var(--input))',
        ring: 'hsl(var(--ring))',
        background: 'hsl(var(--background))',
        foreground: 'hsl(var(--foreground))',
        primary: {
          DEFAULT: 'hsl(var(--primary))',
          foreground: 'hsl(var(--primary-foreground))',
        },
        secondary: {
          DEFAULT: 'hsl(var(--secondary))',
          foreground: 'hsl(var(--secondary-foreground))',
        },
        muted: {
          DEFAULT: 'hsl(var(--muted))',
          foreground: 'hsl(var(--muted-foreground))',
        },
        card: {
          DEFAULT: 'hsl(var(--card))',
          foreground: 'hsl(var(--card-foreground))',
        },
        popover: {
          DEFAULT: 'hsl(var(--popover))',
          foreground: 'hsl(var(--popover-foreground))',
        },
      },
      borderRadius: {
        lg: 'var(--radius)',
        md: 'calc(var(--radius) - 2px)',
        sm: 'calc(var(--radius) - 4px)',
      },
    },
  },
  plugins: [],
}
'''

FILES["frontend/postcss.config.js"] = '''export default {
  plugins: {
    tailwindcss: {},
    autoprefixer: {},
  },
}
'''

FILES["frontend/tsconfig.json"] = '''{
  "compilerOptions": {
    "target": "ES2020",
    "useDefineForClassFields": true,
    "lib": ["ES2020", "DOM", "DOM.Iterable"],
    "module": "ESNext",
    "skipLibCheck": true,
    "moduleResolution": "bundler",
    "allowImportingTsExtensions": true,
    "resolveJsonModule": true,
    "isolatedModules": true,
    "noEmit": true,
    "jsx": "react-jsx",
    "strict": true,
    "noUnusedLocals": true,
    "noUnusedParameters": true,
    "noFallthroughCasesInSwitch": true,
    "baseUrl": ".",
    "paths": {
      "@/*": ["./src/*"]
    }
  },
  "include": ["src"],
  "references": [{ "path": "./tsconfig.node.json" }]
}
'''

FILES["frontend/tsconfig.node.json"] = '''{
  "compilerOptions": {
    "composite": true,
    "skipLibCheck": true,
    "module": "ESNext",
    "moduleResolution": "bundler",
    "allowSyntheticDefaultImports": true,
    "strict": true
  },
  "include": ["vite.config.ts"]
}
'''

FILES["frontend/index.html"] = '''<!doctype html>
<html lang="en">
  <head>
    <meta charset="UTF-8" />
    <link rel="icon" type="image/svg+xml" href="/vite.svg" />
    <meta name="viewport" content="width=device-width, initial-scale=1.0" />
    <title>Stratum AI</title>
  </head>
  <body>
    <div id="root"></div>
    <script type="module" src="/src/main.tsx"></script>
  </body>
</html>
'''

FILES["frontend/src/main.tsx"] = '''import React from 'react'
import ReactDOM from 'react-dom/client'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import App from './App'
import './index.css'
import './i18n'

const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      staleTime: 5 * 60 * 1000,
      retry: 1,
    },
  },
})

ReactDOM.createRoot(document.getElementById('root')!).render(
  <React.StrictMode>
    <QueryClientProvider client={queryClient}>
      <App />
    </QueryClientProvider>
  </React.StrictMode>,
)
'''

FILES["frontend/src/index.css"] = '''@tailwind base;
@tailwind components;
@tailwind utilities;

@layer base {
  :root {
    --background: 0 0% 100%;
    --foreground: 222.2 84% 4.9%;
    --card: 0 0% 100%;
    --card-foreground: 222.2 84% 4.9%;
    --popover: 0 0% 100%;
    --popover-foreground: 222.2 84% 4.9%;
    --primary: 199 89% 48%;
    --primary-foreground: 210 40% 98%;
    --secondary: 210 40% 96.1%;
    --secondary-foreground: 222.2 47.4% 11.2%;
    --muted: 210 40% 96.1%;
    --muted-foreground: 215.4 16.3% 46.9%;
    --border: 214.3 31.8% 91.4%;
    --input: 214.3 31.8% 91.4%;
    --ring: 199 89% 48%;
    --radius: 0.75rem;
  }

  .dark {
    --background: 222.2 84% 4.9%;
    --foreground: 210 40% 98%;
    --card: 222.2 84% 4.9%;
    --card-foreground: 210 40% 98%;
    --popover: 222.2 84% 4.9%;
    --popover-foreground: 210 40% 98%;
    --primary: 199 89% 48%;
    --primary-foreground: 222.2 47.4% 11.2%;
    --secondary: 217.2 32.6% 17.5%;
    --secondary-foreground: 210 40% 98%;
    --muted: 217.2 32.6% 17.5%;
    --muted-foreground: 215 20.2% 65.1%;
    --border: 217.2 32.6% 17.5%;
    --input: 217.2 32.6% 17.5%;
    --ring: 212.7 26.8% 83.9%;
  }
}

@layer base {
  * {
    @apply border-border;
  }
  body {
    @apply bg-background text-foreground;
  }
}
'''

FILES["frontend/src/i18n.ts"] = '''import i18n from 'i18next'
import { initReactI18next } from 'react-i18next'

import en from './i18n/locales/en/translation.json'
import uk from './i18n/locales/uk/translation.json'

i18n.use(initReactI18next).init({
  resources: {
    en: { translation: en },
    uk: { translation: uk },
  },
  lng: 'en',
  fallbackLng: 'en',
  interpolation: {
    escapeValue: false,
  },
})

export default i18n
'''

FILES["frontend/src/i18n/locales/en/translation.json"] = '''{
  "common": {
    "save": "Save",
    "cancel": "Cancel",
    "delete": "Delete",
    "edit": "Edit",
    "create": "Create",
    "search": "Search",
    "filter": "Filter",
    "export": "Export",
    "loading": "Loading...",
    "viewAll": "View All",
    "previous": "Previous",
    "next": "Next",
    "moreFilters": "More Filters"
  },
  "nav": {
    "overview": "Overview",
    "campaigns": "Campaigns",
    "stratum": "Stratum AI",
    "benchmarks": "Benchmarks",
    "assets": "Assets",
    "rules": "Rules",
    "settings": "Settings"
  },
  "overview": {
    "title": "Dashboard Overview",
    "subtitle": "Monitor your marketing performance across all channels",
    "performanceTrend": "Performance Trend",
    "roasTrend": "ROAS Trend",
    "recentAlerts": "Recent Alerts"
  },
  "campaigns": {
    "title": "Campaigns",
    "subtitle": "Manage your advertising campaigns",
    "createNew": "Create Campaign",
    "searchPlaceholder": "Search campaigns...",
    "allStatuses": "All Statuses",
    "allPlatforms": "All Platforms",
    "active": "Active",
    "paused": "Paused",
    "completed": "Completed",
    "draft": "Draft",
    "name": "Campaign",
    "status": "Status",
    "spend": "Spend",
    "revenue": "Revenue",
    "conversions": "Conversions",
    "trend": "Trend",
    "actions": "Actions",
    "noResults": "No campaigns found",
    "selected": "selected"
  },
  "kpi": {
    "spend": "Total Spend",
    "revenue": "Revenue",
    "impressions": "Impressions",
    "clicks": "Clicks",
    "conversions": "Conversions",
    "spendTooltip": "Total advertising spend across all active campaigns",
    "revenueTooltip": "Total revenue attributed to your campaigns",
    "roasTooltip": "Return on Ad Spend - revenue divided by spend",
    "impressionsTooltip": "Total number of times your ads were displayed",
    "clicksTooltip": "Total number of clicks on your ads",
    "ctrTooltip": "Click-Through Rate - percentage of impressions that resulted in clicks",
    "conversionsTooltip": "Total number of conversions (purchases, signups, etc.)",
    "cpaTooltip": "Cost Per Acquisition - average cost to acquire one conversion"
  },
  "simulator": {
    "title": "What-If Simulator",
    "budget": "Budget Change",
    "bid": "Bid Adjustment",
    "audience": "Audience Expansion",
    "budgetTooltip": "Simulate the impact of changing your campaign budget",
    "bidTooltip": "Simulate the impact of adjusting your bid strategy",
    "audienceTooltip": "Simulate the impact of expanding or narrowing your target audience",
    "projectedResults": "Projected Results",
    "confidence": "confidence",
    "spend": "Spend",
    "revenue": "Revenue",
    "impressions": "Impressions",
    "clicks": "Clicks",
    "conversions": "Conversions",
    "adjustSliders": "Adjust the sliders above to see projected results"
  },
  "settings": {
    "title": "Settings",
    "subtitle": "Manage your account and preferences",
    "profile": "Profile",
    "organization": "Organization",
    "notifications": "Notifications",
    "security": "Security",
    "integrations": "Integrations",
    "preferences": "Preferences",
    "billing": "Billing",
    "gdpr": "Privacy & Data"
  },
  "dateRange": {
    "today": "Today",
    "yesterday": "Yesterday",
    "last7days": "Last 7 Days",
    "last30days": "Last 30 Days",
    "thisMonth": "This Month",
    "lastMonth": "Last Month"
  }
}
'''

FILES["frontend/src/i18n/locales/uk/translation.json"] = '''{
  "common": {
    "save": "Зберегти",
    "cancel": "Скасувати",
    "delete": "Видалити",
    "edit": "Редагувати",
    "create": "Створити",
    "search": "Пошук",
    "filter": "Фільтр",
    "export": "Експорт",
    "loading": "Завантаження...",
    "viewAll": "Переглянути все",
    "previous": "Попередня",
    "next": "Наступна",
    "moreFilters": "Більше фільтрів"
  },
  "nav": {
    "overview": "Огляд",
    "campaigns": "Кампанії",
    "stratum": "Stratum AI",
    "benchmarks": "Бенчмарки",
    "assets": "Активи",
    "rules": "Правила",
    "settings": "Налаштування"
  },
  "overview": {
    "title": "Огляд панелі",
    "subtitle": "Моніторинг маркетингової ефективності на всіх каналах",
    "performanceTrend": "Тренд ефективності",
    "roasTrend": "Тренд ROAS",
    "recentAlerts": "Останні сповіщення"
  },
  "campaigns": {
    "title": "Кампанії",
    "subtitle": "Керуйте вашими рекламними кампаніями",
    "createNew": "Створити кампанію",
    "searchPlaceholder": "Пошук кампаній...",
    "allStatuses": "Всі статуси",
    "allPlatforms": "Всі платформи",
    "active": "Активні",
    "paused": "Призупинені",
    "completed": "Завершені",
    "draft": "Чернетки"
  },
  "kpi": {
    "spend": "Витрати",
    "revenue": "Дохід",
    "impressions": "Покази",
    "clicks": "Кліки",
    "conversions": "Конверсії"
  },
  "simulator": {
    "title": "Симулятор",
    "budget": "Зміна бюджету",
    "bid": "Коригування ставки",
    "audience": "Розширення аудиторії",
    "projectedResults": "Прогнозовані результати"
  },
  "settings": {
    "title": "Налаштування",
    "subtitle": "Керуйте вашим акаунтом та налаштуваннями"
  },
  "dateRange": {
    "today": "Сьогодні",
    "yesterday": "Вчора",
    "last7days": "Останні 7 днів",
    "last30days": "Останні 30 днів",
    "thisMonth": "Цей місяць",
    "lastMonth": "Минулий місяць"
  }
}
'''


# =============================================================================
# Script Execution
# =============================================================================

def create_project_structure(target_dir: Path) -> None:
    """Create the project directory structure and files."""
    print(f"\\n{'='*60}")
    print(f"  Stratum AI - Project Initialization")
    print(f"{'='*60}\\n")
    print(f"Target directory: {target_dir}\\n")

    # Create target directory if it doesn't exist
    target_dir.mkdir(parents=True, exist_ok=True)

    # Create directories
    print("Creating directories...")
    for directory in DIRECTORIES:
        dir_path = target_dir / directory
        dir_path.mkdir(parents=True, exist_ok=True)
        print(f"  [+] {directory}/")

    # Create files
    print("\\nCreating files...")
    for file_path, content in FILES.items():
        full_path = target_dir / file_path

        # Ensure parent directory exists
        full_path.parent.mkdir(parents=True, exist_ok=True)

        # Write file content
        with open(full_path, "w", encoding="utf-8") as f:
            f.write(content.lstrip("\\n"))

        print(f"  [+] {file_path}")

    print(f"\\n{'='*60}")
    print("  Project initialization complete!")
    print(f"{'='*60}\\n")
    print("Next steps:")
    print(f"  1. cd {target_dir}")
    print("  2. cp .env.example .env")
    print("  3. docker-compose up -d")
    print("  4. docker-compose exec api alembic upgrade head")
    print("  5. Open http://localhost:5173 in your browser")
    print("\\n")


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="Initialize Stratum AI project structure"
    )
    parser.add_argument(
        "--target-dir",
        type=str,
        default="./stratum-ai",
        help="Target directory for project creation (default: ./stratum-ai)"
    )

    args = parser.parse_args()
    target_dir = Path(args.target_dir).resolve()

    try:
        create_project_structure(target_dir)
    except Exception as e:
        print(f"\\nError: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
'''
