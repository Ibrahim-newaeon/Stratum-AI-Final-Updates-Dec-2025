#!/bin/bash
# =============================================================================
# Stratum AI - Production Deployment Script
# =============================================================================
# This script automates the deployment of Stratum AI to a production server.
#
# Usage:
#   ./deploy.sh [command]
#
# Commands:
#   setup       - Initial server setup (Docker, Nginx, Certbot)
#   configure   - Generate production .env file
#   ssl         - Generate SSL certificates
#   deploy      - Deploy application
#   update      - Update to latest version
#   backup      - Create database backup
#   restore     - Restore from backup
#   logs        - View application logs
#   status      - Check service status
#   full        - Run complete deployment (setup + configure + ssl + deploy)
#
# =============================================================================

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Configuration
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"
BACKUP_DIR="${PROJECT_DIR}/backups"
LOG_FILE="${PROJECT_DIR}/deploy.log"

# Default values (can be overridden by .env)
DOMAIN_API="${DOMAIN_API:-api.example.com}"
DOMAIN_APP="${DOMAIN_APP:-app.example.com}"
ADMIN_EMAIL="${ADMIN_EMAIL:-admin@example.com}"

# =============================================================================
# Helper Functions
# =============================================================================

log() {
    echo -e "${GREEN}[$(date +'%Y-%m-%d %H:%M:%S')]${NC} $1" | tee -a "$LOG_FILE"
}

warn() {
    echo -e "${YELLOW}[WARNING]${NC} $1" | tee -a "$LOG_FILE"
}

error() {
    echo -e "${RED}[ERROR]${NC} $1" | tee -a "$LOG_FILE"
    exit 1
}

info() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

confirm() {
    read -p "$1 [y/N] " response
    case "$response" in
        [yY][eE][sS]|[yY])
            return 0
            ;;
        *)
            return 1
            ;;
    esac
}

generate_secret() {
    python3 -c "import secrets; print(secrets.token_urlsafe($1))"
}

generate_encryption_key() {
    python3 -c "import secrets, base64; print(base64.urlsafe_b64encode(secrets.token_bytes(32)).decode())"
}

# =============================================================================
# Setup Functions
# =============================================================================

check_root() {
    if [[ $EUID -ne 0 ]]; then
        error "This script must be run as root (use sudo)"
    fi
}

check_requirements() {
    log "Checking system requirements..."

    # Check OS
    if [[ ! -f /etc/debian_version ]] && [[ ! -f /etc/redhat-release ]]; then
        warn "This script is designed for Debian/Ubuntu or RHEL/CentOS"
    fi

    # Check memory
    total_mem=$(free -m | awk '/^Mem:/{print $2}')
    if [[ $total_mem -lt 3500 ]]; then
        warn "Recommended minimum RAM is 4GB. Current: ${total_mem}MB"
    fi

    # Check disk space
    available_space=$(df -BG / | awk 'NR==2 {print $4}' | tr -d 'G')
    if [[ $available_space -lt 20 ]]; then
        warn "Recommended minimum disk space is 20GB. Available: ${available_space}GB"
    fi

    log "System requirements check completed"
}

install_docker() {
    log "Installing Docker..."

    if command -v docker &> /dev/null; then
        log "Docker is already installed: $(docker --version)"
        return 0
    fi

    # Install Docker
    curl -fsSL https://get.docker.com | sh

    # Start and enable Docker
    systemctl start docker
    systemctl enable docker

    # Install Docker Compose plugin
    apt-get update
    apt-get install -y docker-compose-plugin

    log "Docker installed successfully: $(docker --version)"
}

install_nginx() {
    log "Installing Nginx..."

    if command -v nginx &> /dev/null; then
        log "Nginx is already installed"
        return 0
    fi

    apt-get update
    apt-get install -y nginx

    systemctl start nginx
    systemctl enable nginx

    log "Nginx installed successfully"
}

install_certbot() {
    log "Installing Certbot..."

    if command -v certbot &> /dev/null; then
        log "Certbot is already installed"
        return 0
    fi

    apt-get update
    apt-get install -y certbot python3-certbot-nginx

    log "Certbot installed successfully"
}

setup_firewall() {
    log "Configuring firewall..."

    if command -v ufw &> /dev/null; then
        ufw allow 22/tcp
        ufw allow 80/tcp
        ufw allow 443/tcp
        ufw --force enable
        log "UFW firewall configured"
    else
        warn "UFW not installed, skipping firewall configuration"
    fi
}

setup_server() {
    check_root
    check_requirements

    log "Starting server setup..."

    # Update system
    log "Updating system packages..."
    apt-get update && apt-get upgrade -y

    # Install essential tools
    apt-get install -y curl git htop vim unzip jq python3 python3-pip

    install_docker
    install_nginx
    install_certbot
    setup_firewall

    # Create backup directory
    mkdir -p "$BACKUP_DIR"

    log "Server setup completed successfully!"
}

# =============================================================================
# Configuration Functions
# =============================================================================

configure_env() {
    log "Configuring environment..."

    ENV_FILE="${PROJECT_DIR}/.env"
    ENV_EXAMPLE="${PROJECT_DIR}/.env.example"

    if [[ -f "$ENV_FILE" ]]; then
        if ! confirm "Existing .env file found. Overwrite?"; then
            log "Keeping existing .env file"
            return 0
        fi
        cp "$ENV_FILE" "${ENV_FILE}.backup.$(date +%Y%m%d_%H%M%S)"
    fi

    # Prompt for configuration
    echo ""
    info "Please provide the following configuration:"
    echo ""

    read -p "API Domain (e.g., api.yourdomain.com): " DOMAIN_API
    read -p "App Domain (e.g., app.yourdomain.com): " DOMAIN_APP
    read -p "Admin Email: " ADMIN_EMAIL
    read -p "Database Password (leave empty to generate): " DB_PASSWORD

    if [[ -z "$DB_PASSWORD" ]]; then
        DB_PASSWORD=$(generate_secret 24)
    fi

    # Generate secrets
    SECRET_KEY=$(generate_secret 48)
    JWT_SECRET=$(generate_secret 48)
    PII_KEY=$(generate_encryption_key)

    # Create .env file
    cat > "$ENV_FILE" << EOF
# =============================================================================
# Stratum AI - Production Configuration
# Generated on $(date)
# =============================================================================

# Application
APP_NAME=StratumAI
APP_ENV=production
DEBUG=false
SECRET_KEY=${SECRET_KEY}
API_V1_PREFIX=/api/v1

# Database
POSTGRES_USER=stratum
POSTGRES_PASSWORD=${DB_PASSWORD}
POSTGRES_DB=stratum_ai
DATABASE_URL=postgresql+asyncpg://stratum:${DB_PASSWORD}@db:5432/stratum_ai
DATABASE_URL_SYNC=postgresql://stratum:${DB_PASSWORD}@db:5432/stratum_ai
DB_POOL_SIZE=20
DB_MAX_OVERFLOW=10

# Redis
REDIS_URL=redis://redis:6379/0
CELERY_BROKER_URL=redis://redis:6379/1
CELERY_RESULT_BACKEND=redis://redis:6379/2

# JWT
JWT_SECRET_KEY=${JWT_SECRET}
JWT_ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=30
REFRESH_TOKEN_EXPIRE_DAYS=7

# Encryption
PII_ENCRYPTION_KEY=${PII_KEY}

# CORS
CORS_ORIGINS=https://${DOMAIN_APP}
CORS_ALLOW_CREDENTIALS=true

# Frontend URL
FRONTEND_URL=https://${DOMAIN_APP}

# Email (configure for production)
SMTP_HOST=
SMTP_PORT=587
SMTP_USER=
SMTP_PASSWORD=
SMTP_TLS=true
FROM_EMAIL=noreply@${DOMAIN_APP}
FROM_NAME=Stratum AI

# ML Configuration
ML_PROVIDER=local
ML_MODELS_PATH=/app/ml_service/models

# Ad Platforms (set USE_MOCK_AD_DATA=false for real APIs)
USE_MOCK_AD_DATA=true

# Rate Limiting
RATE_LIMIT_PER_MINUTE=500
RATE_LIMIT_BURST=100

# Logging
LOG_LEVEL=INFO
LOG_FORMAT=json

# Monitoring (optional)
SENTRY_DSN=

# Feature Flags
FEATURE_COMPETITOR_INTEL=true
FEATURE_WHAT_IF_SIMULATOR=true
FEATURE_AUTOMATION_RULES=true
FEATURE_GDPR_COMPLIANCE=true
EOF

    chmod 600 "$ENV_FILE"

    log "Environment configuration saved to .env"
    info "Database Password: ${DB_PASSWORD}"
    warn "Please save your database password securely!"
}

# =============================================================================
# SSL Functions
# =============================================================================

setup_ssl() {
    log "Setting up SSL certificates..."

    if [[ -z "$DOMAIN_API" ]] || [[ -z "$DOMAIN_APP" ]]; then
        # Try to read from .env
        if [[ -f "${PROJECT_DIR}/.env" ]]; then
            source "${PROJECT_DIR}/.env" 2>/dev/null || true
        fi

        read -p "API Domain: " DOMAIN_API
        read -p "App Domain: " DOMAIN_APP
        read -p "Admin Email: " ADMIN_EMAIL
    fi

    # Stop nginx temporarily
    systemctl stop nginx || true

    # Get certificates
    certbot certonly --standalone \
        -d "$DOMAIN_API" \
        -d "$DOMAIN_APP" \
        --email "$ADMIN_EMAIL" \
        --agree-tos \
        --non-interactive

    # Setup auto-renewal
    (crontab -l 2>/dev/null; echo "0 0 1 * * certbot renew --quiet && systemctl reload nginx") | crontab -

    log "SSL certificates generated successfully"
}

# =============================================================================
# Nginx Functions
# =============================================================================

configure_nginx() {
    log "Configuring Nginx..."

    if [[ -z "$DOMAIN_API" ]] || [[ -z "$DOMAIN_APP" ]]; then
        read -p "API Domain: " DOMAIN_API
        read -p "App Domain: " DOMAIN_APP
    fi

    # Create Nginx configuration
    cat > /etc/nginx/sites-available/stratum << EOF
# =============================================================================
# Stratum AI - Nginx Configuration
# =============================================================================

# Rate limiting
limit_req_zone \$binary_remote_addr zone=api_limit:10m rate=100r/s;
limit_req_zone \$binary_remote_addr zone=login_limit:10m rate=5r/s;

# API Backend
upstream stratum_api {
    server 127.0.0.1:8000;
    keepalive 32;
}

# Frontend Backend
upstream stratum_frontend {
    server 127.0.0.1:5173;
    keepalive 16;
}

# Redirect HTTP to HTTPS
server {
    listen 80;
    server_name ${DOMAIN_API} ${DOMAIN_APP};
    return 301 https://\$server_name\$request_uri;
}

# API Server
server {
    listen 443 ssl http2;
    server_name ${DOMAIN_API};

    # SSL Configuration
    ssl_certificate /etc/letsencrypt/live/${DOMAIN_API}/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/${DOMAIN_API}/privkey.pem;
    ssl_session_timeout 1d;
    ssl_session_cache shared:SSL:50m;
    ssl_session_tickets off;
    ssl_protocols TLSv1.2 TLSv1.3;
    ssl_ciphers ECDHE-ECDSA-AES128-GCM-SHA256:ECDHE-RSA-AES128-GCM-SHA256:ECDHE-ECDSA-AES256-GCM-SHA384:ECDHE-RSA-AES256-GCM-SHA384;
    ssl_prefer_server_ciphers off;

    # Security Headers
    add_header X-Frame-Options "SAMEORIGIN" always;
    add_header X-Content-Type-Options "nosniff" always;
    add_header X-XSS-Protection "1; mode=block" always;
    add_header Referrer-Policy "strict-origin-when-cross-origin" always;
    add_header Content-Security-Policy "default-src 'self'; script-src 'self' 'unsafe-inline'; style-src 'self' 'unsafe-inline';" always;

    # Gzip
    gzip on;
    gzip_vary on;
    gzip_proxied any;
    gzip_comp_level 6;
    gzip_types text/plain text/css text/xml application/json application/javascript application/rss+xml application/atom+xml image/svg+xml;

    # Client body size
    client_max_body_size 50M;

    # Logging
    access_log /var/log/nginx/stratum_api_access.log;
    error_log /var/log/nginx/stratum_api_error.log;

    # Health check (no rate limit)
    location /health {
        proxy_pass http://stratum_api;
        proxy_http_version 1.1;
        proxy_set_header Host \$host;
        proxy_set_header X-Real-IP \$remote_addr;
        proxy_set_header X-Forwarded-For \$proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto \$scheme;
    }

    # Login endpoint (strict rate limit)
    location /api/v1/auth/login {
        limit_req zone=login_limit burst=10 nodelay;
        proxy_pass http://stratum_api;
        proxy_http_version 1.1;
        proxy_set_header Host \$host;
        proxy_set_header X-Real-IP \$remote_addr;
        proxy_set_header X-Forwarded-For \$proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto \$scheme;
    }

    # SSE endpoint (long-lived connections)
    location /api/v1/events/stream {
        proxy_pass http://stratum_api;
        proxy_http_version 1.1;
        proxy_set_header Connection "";
        proxy_set_header Host \$host;
        proxy_set_header X-Real-IP \$remote_addr;
        proxy_set_header X-Forwarded-For \$proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto \$scheme;
        proxy_buffering off;
        proxy_cache off;
        proxy_read_timeout 86400s;
        proxy_send_timeout 86400s;
    }

    # WebSocket support
    location /ws {
        proxy_pass http://stratum_api;
        proxy_http_version 1.1;
        proxy_set_header Upgrade \$http_upgrade;
        proxy_set_header Connection "upgrade";
        proxy_set_header Host \$host;
        proxy_set_header X-Real-IP \$remote_addr;
        proxy_set_header X-Forwarded-For \$proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto \$scheme;
        proxy_read_timeout 86400s;
    }

    # API endpoints
    location / {
        limit_req zone=api_limit burst=50 nodelay;
        proxy_pass http://stratum_api;
        proxy_http_version 1.1;
        proxy_set_header Upgrade \$http_upgrade;
        proxy_set_header Connection "upgrade";
        proxy_set_header Host \$host;
        proxy_set_header X-Real-IP \$remote_addr;
        proxy_set_header X-Forwarded-For \$proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto \$scheme;
        proxy_read_timeout 300s;
        proxy_connect_timeout 75s;
    }
}

# Frontend Server
server {
    listen 443 ssl http2;
    server_name ${DOMAIN_APP};

    # SSL Configuration
    ssl_certificate /etc/letsencrypt/live/${DOMAIN_API}/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/${DOMAIN_API}/privkey.pem;
    ssl_session_timeout 1d;
    ssl_session_cache shared:SSL:50m;
    ssl_protocols TLSv1.2 TLSv1.3;
    ssl_prefer_server_ciphers off;

    # Security Headers
    add_header X-Frame-Options "SAMEORIGIN" always;
    add_header X-Content-Type-Options "nosniff" always;
    add_header X-XSS-Protection "1; mode=block" always;

    # Gzip
    gzip on;
    gzip_vary on;
    gzip_types text/plain text/css text/xml application/json application/javascript;

    # Logging
    access_log /var/log/nginx/stratum_app_access.log;
    error_log /var/log/nginx/stratum_app_error.log;

    # Frontend proxy
    location / {
        proxy_pass http://stratum_frontend;
        proxy_http_version 1.1;
        proxy_set_header Upgrade \$http_upgrade;
        proxy_set_header Connection "upgrade";
        proxy_set_header Host \$host;
        proxy_set_header X-Real-IP \$remote_addr;
        proxy_set_header X-Forwarded-For \$proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto \$scheme;
    }

    # Static assets caching
    location ~* \.(js|css|png|jpg|jpeg|gif|ico|svg|woff|woff2)$ {
        proxy_pass http://stratum_frontend;
        proxy_http_version 1.1;
        proxy_set_header Host \$host;
        expires 1y;
        add_header Cache-Control "public, immutable";
    }
}
EOF

    # Enable site
    ln -sf /etc/nginx/sites-available/stratum /etc/nginx/sites-enabled/
    rm -f /etc/nginx/sites-enabled/default

    # Test configuration
    nginx -t

    # Reload Nginx
    systemctl reload nginx

    log "Nginx configured successfully"
}

# =============================================================================
# Deployment Functions
# =============================================================================

deploy_app() {
    log "Deploying Stratum AI..."

    cd "$PROJECT_DIR"

    # Check for .env
    if [[ ! -f ".env" ]]; then
        error ".env file not found. Run './deploy.sh configure' first"
    fi

    # Pull latest changes (if git repo)
    if [[ -d ".git" ]]; then
        log "Pulling latest changes..."
        git pull origin main || git pull origin master || true
    fi

    # Build and start services
    log "Building Docker images..."
    docker compose -f docker-compose.yml -f docker-compose.prod.yml build

    log "Starting services..."
    docker compose -f docker-compose.yml -f docker-compose.prod.yml up -d

    # Wait for services to be healthy
    log "Waiting for services to start..."
    sleep 10

    # Run migrations
    log "Running database migrations..."
    docker compose exec -T api alembic upgrade head

    # Health check
    log "Performing health check..."
    for i in {1..30}; do
        if curl -sf http://localhost:8000/health > /dev/null 2>&1; then
            log "API is healthy!"
            break
        fi
        if [[ $i -eq 30 ]]; then
            error "Health check failed after 30 attempts"
        fi
        sleep 2
    done

    log "Deployment completed successfully!"
    echo ""
    info "Application is now running at:"
    info "  API: https://${DOMAIN_API}"
    info "  App: https://${DOMAIN_APP}"
}

update_app() {
    log "Updating Stratum AI..."

    cd "$PROJECT_DIR"

    # Create backup first
    backup_database

    # Pull latest changes
    if [[ -d ".git" ]]; then
        git pull origin main || git pull origin master
    fi

    # Rebuild and restart
    docker compose -f docker-compose.yml -f docker-compose.prod.yml build
    docker compose -f docker-compose.yml -f docker-compose.prod.yml up -d

    # Run migrations
    docker compose exec -T api alembic upgrade head

    log "Update completed successfully!"
}

# =============================================================================
# Backup Functions
# =============================================================================

backup_database() {
    log "Creating database backup..."

    cd "$PROJECT_DIR"
    mkdir -p "$BACKUP_DIR"

    BACKUP_FILE="${BACKUP_DIR}/db_$(date +%Y%m%d_%H%M%S).sql.gz"

    docker compose exec -T db pg_dump -U stratum stratum_ai | gzip > "$BACKUP_FILE"

    # Keep only last 30 days of backups
    find "$BACKUP_DIR" -name "db_*.sql.gz" -mtime +30 -delete

    log "Backup saved to: $BACKUP_FILE"
}

restore_database() {
    log "Restoring database..."

    cd "$PROJECT_DIR"

    # List available backups
    echo ""
    info "Available backups:"
    ls -la "$BACKUP_DIR"/*.sql.gz 2>/dev/null || error "No backups found"
    echo ""

    read -p "Enter backup filename: " BACKUP_FILE

    if [[ ! -f "${BACKUP_DIR}/${BACKUP_FILE}" ]]; then
        error "Backup file not found: ${BACKUP_FILE}"
    fi

    if confirm "This will overwrite the current database. Continue?"; then
        gunzip -c "${BACKUP_DIR}/${BACKUP_FILE}" | docker compose exec -T db psql -U stratum stratum_ai
        log "Database restored from: $BACKUP_FILE"
    fi
}

# =============================================================================
# Status Functions
# =============================================================================

show_status() {
    cd "$PROJECT_DIR"

    echo ""
    info "=== Service Status ==="
    docker compose ps

    echo ""
    info "=== Health Check ==="
    curl -s http://localhost:8000/health | jq . || echo "API not responding"

    echo ""
    info "=== Resource Usage ==="
    docker stats --no-stream

    echo ""
    info "=== Recent Logs ==="
    docker compose logs --tail=20 api
}

show_logs() {
    cd "$PROJECT_DIR"

    SERVICE="${2:-api}"
    docker compose logs -f "$SERVICE"
}

# =============================================================================
# Main
# =============================================================================

print_usage() {
    echo ""
    echo "Stratum AI Deployment Script"
    echo ""
    echo "Usage: $0 [command]"
    echo ""
    echo "Commands:"
    echo "  setup       - Initial server setup (Docker, Nginx, Certbot)"
    echo "  configure   - Generate production .env file"
    echo "  ssl         - Generate SSL certificates"
    echo "  nginx       - Configure Nginx"
    echo "  deploy      - Deploy application"
    echo "  update      - Update to latest version"
    echo "  backup      - Create database backup"
    echo "  restore     - Restore from backup"
    echo "  logs [svc]  - View logs (default: api)"
    echo "  status      - Check service status"
    echo "  full        - Complete deployment (setup + configure + ssl + nginx + deploy)"
    echo ""
}

main() {
    case "${1:-}" in
        setup)
            setup_server
            ;;
        configure)
            configure_env
            ;;
        ssl)
            setup_ssl
            ;;
        nginx)
            configure_nginx
            ;;
        deploy)
            deploy_app
            ;;
        update)
            update_app
            ;;
        backup)
            backup_database
            ;;
        restore)
            restore_database
            ;;
        logs)
            show_logs "$@"
            ;;
        status)
            show_status
            ;;
        full)
            setup_server
            configure_env
            setup_ssl
            configure_nginx
            deploy_app
            ;;
        *)
            print_usage
            ;;
    esac
}

main "$@"
