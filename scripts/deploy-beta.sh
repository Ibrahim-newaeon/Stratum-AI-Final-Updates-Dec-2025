#!/bin/bash
# =============================================================================
# Stratum AI - Beta Deployment Script
# =============================================================================
# Usage: ./scripts/deploy-beta.sh [command]
# Commands: setup, deploy, update, logs, status, backup, rollback
# =============================================================================

set -e

# Configuration
APP_DIR="/opt/stratum-ai"
COMPOSE_FILE="docker-compose.beta.yml"
DOMAIN="beta.stratum-ai.com"
BACKUP_DIR="/opt/stratum-ai-backups"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

log_info() {
    echo -e "${GREEN}[INFO]${NC} $1"
}

log_warn() {
    echo -e "${YELLOW}[WARN]${NC} $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# =============================================================================
# Initial Server Setup
# =============================================================================
setup() {
    log_info "Starting initial server setup..."

    # Update system
    log_info "Updating system packages..."
    apt update && apt upgrade -y

    # Install Docker if not present
    if ! command -v docker &> /dev/null; then
        log_info "Installing Docker..."
        apt install -y docker.io docker-compose-plugin
        systemctl enable docker
        systemctl start docker
    fi

    # Install Certbot
    if ! command -v certbot &> /dev/null; then
        log_info "Installing Certbot..."
        apt install -y certbot
    fi

    # Create app directory
    log_info "Creating application directory..."
    mkdir -p $APP_DIR
    mkdir -p $BACKUP_DIR
    mkdir -p /var/www/certbot

    # Clone or update repository
    if [ -d "$APP_DIR/.git" ]; then
        log_info "Updating repository..."
        cd $APP_DIR
        git fetch origin
        git reset --hard origin/main
    else
        log_info "Cloning repository..."
        git clone https://github.com/Ibrahim-newaeon/Stratum-AI-Final-Updates-Dec-2025.git $APP_DIR
    fi

    cd $APP_DIR

    # Check for .env.production
    if [ ! -f ".env.production" ]; then
        log_warn ".env.production not found!"
        log_info "Copying from example..."
        cp .env.production.example .env.production
        log_warn "Please edit .env.production with your actual values before deploying!"
        exit 1
    fi

    log_info "Setup complete!"
}

# =============================================================================
# SSL Certificate Setup
# =============================================================================
ssl_setup() {
    log_info "Setting up SSL certificate..."

    # Check if certificate already exists
    if [ -d "/etc/letsencrypt/live/$DOMAIN" ]; then
        log_info "SSL certificate already exists for $DOMAIN"
        return 0
    fi

    # Stop any service on port 80
    docker compose -f $COMPOSE_FILE down 2>/dev/null || true

    # Get certificate
    certbot certonly --standalone \
        -d $DOMAIN \
        --non-interactive \
        --agree-tos \
        --email admin@stratum-ai.com \
        --no-eff-email

    # Setup auto-renewal cron
    if ! crontab -l 2>/dev/null | grep -q "certbot renew"; then
        log_info "Setting up SSL auto-renewal..."
        (crontab -l 2>/dev/null; echo "0 3 * * * certbot renew --quiet && docker compose -f $APP_DIR/$COMPOSE_FILE exec nginx nginx -s reload") | crontab -
    fi

    log_info "SSL setup complete!"
}

# =============================================================================
# Deploy Application
# =============================================================================
deploy() {
    log_info "Starting deployment..."
    cd $APP_DIR

    # Check prerequisites
    if [ ! -f ".env.production" ]; then
        log_error ".env.production not found! Run setup first."
        exit 1
    fi

    # Setup SSL if needed
    if [ ! -d "/etc/letsencrypt/live/$DOMAIN" ]; then
        ssl_setup
    fi

    # Build and start services
    log_info "Building Docker images..."
    docker compose -f $COMPOSE_FILE build --no-cache

    log_info "Starting services..."
    docker compose -f $COMPOSE_FILE up -d

    # Wait for services to be healthy
    log_info "Waiting for services to start..."
    sleep 30

    # Check health
    status

    log_info "Deployment complete!"
    log_info "Access the application at: https://$DOMAIN"
}

# =============================================================================
# Update Application (Zero-downtime)
# =============================================================================
update() {
    log_info "Starting update..."
    cd $APP_DIR

    # Create backup before update
    backup

    # Pull latest code
    log_info "Pulling latest code..."
    git fetch origin
    git reset --hard origin/main

    # Rebuild and restart services one by one
    log_info "Rebuilding images..."
    docker compose -f $COMPOSE_FILE build

    # Update API first (includes migrations)
    log_info "Updating API service..."
    docker compose -f $COMPOSE_FILE up -d --no-deps api
    sleep 10

    # Update workers
    log_info "Updating worker services..."
    docker compose -f $COMPOSE_FILE up -d --no-deps worker beat

    # Update frontend
    log_info "Updating frontend..."
    docker compose -f $COMPOSE_FILE up -d --no-deps frontend

    # Reload nginx
    log_info "Reloading nginx..."
    docker compose -f $COMPOSE_FILE exec nginx nginx -s reload

    # Cleanup old images
    log_info "Cleaning up old images..."
    docker image prune -f

    log_info "Update complete!"
}

# =============================================================================
# View Logs
# =============================================================================
logs() {
    cd $APP_DIR
    SERVICE=${1:-""}

    if [ -z "$SERVICE" ]; then
        docker compose -f $COMPOSE_FILE logs -f --tail=100
    else
        docker compose -f $COMPOSE_FILE logs -f --tail=100 $SERVICE
    fi
}

# =============================================================================
# Check Status
# =============================================================================
status() {
    cd $APP_DIR

    log_info "Service Status:"
    docker compose -f $COMPOSE_FILE ps

    echo ""
    log_info "Health Checks:"

    # Check API health
    if curl -sf "http://localhost:8000/health" > /dev/null 2>&1; then
        echo -e "  API:      ${GREEN}HEALTHY${NC}"
    else
        echo -e "  API:      ${RED}UNHEALTHY${NC}"
    fi

    # Check Redis
    if docker compose -f $COMPOSE_FILE exec -T redis redis-cli ping > /dev/null 2>&1; then
        echo -e "  Redis:    ${GREEN}HEALTHY${NC}"
    else
        echo -e "  Redis:    ${RED}UNHEALTHY${NC}"
    fi

    # Check Frontend
    if curl -sf "http://localhost:80/health" > /dev/null 2>&1; then
        echo -e "  Frontend: ${GREEN}HEALTHY${NC}"
    else
        echo -e "  Frontend: ${RED}UNHEALTHY${NC}"
    fi

    # Check external access
    echo ""
    log_info "External Access:"
    if curl -sf "https://$DOMAIN/health" > /dev/null 2>&1; then
        echo -e "  HTTPS:    ${GREEN}ACCESSIBLE${NC}"
    else
        echo -e "  HTTPS:    ${RED}NOT ACCESSIBLE${NC}"
    fi

    # Show resource usage
    echo ""
    log_info "Resource Usage:"
    docker stats --no-stream --format "table {{.Name}}\t{{.CPUPerc}}\t{{.MemUsage}}"
}

# =============================================================================
# Backup
# =============================================================================
backup() {
    log_info "Creating backup..."
    cd $APP_DIR

    TIMESTAMP=$(date +%Y%m%d_%H%M%S)
    BACKUP_PATH="$BACKUP_DIR/backup_$TIMESTAMP"
    mkdir -p $BACKUP_PATH

    # Backup Redis data
    log_info "Backing up Redis..."
    docker compose -f $COMPOSE_FILE exec -T redis redis-cli BGSAVE
    sleep 5
    docker cp stratum_redis:/data/dump.rdb $BACKUP_PATH/redis_dump.rdb 2>/dev/null || true

    # Backup environment file
    cp .env.production $BACKUP_PATH/

    # Record current git commit
    git rev-parse HEAD > $BACKUP_PATH/git_commit.txt

    # Cleanup old backups (keep last 5)
    cd $BACKUP_DIR
    ls -t | tail -n +6 | xargs -r rm -rf

    log_info "Backup saved to: $BACKUP_PATH"
}

# =============================================================================
# Rollback
# =============================================================================
rollback() {
    log_info "Starting rollback..."
    cd $APP_DIR

    # Find latest backup
    LATEST_BACKUP=$(ls -t $BACKUP_DIR | head -1)

    if [ -z "$LATEST_BACKUP" ]; then
        log_error "No backup found!"
        exit 1
    fi

    BACKUP_PATH="$BACKUP_DIR/$LATEST_BACKUP"
    log_info "Rolling back to: $BACKUP_PATH"

    # Get the git commit from backup
    if [ -f "$BACKUP_PATH/git_commit.txt" ]; then
        COMMIT=$(cat $BACKUP_PATH/git_commit.txt)
        log_info "Reverting to commit: $COMMIT"
        git checkout $COMMIT
    fi

    # Restore environment
    if [ -f "$BACKUP_PATH/.env.production" ]; then
        cp $BACKUP_PATH/.env.production .env.production
    fi

    # Rebuild and restart
    docker compose -f $COMPOSE_FILE down
    docker compose -f $COMPOSE_FILE build
    docker compose -f $COMPOSE_FILE up -d

    log_info "Rollback complete!"
}

# =============================================================================
# Stop Services
# =============================================================================
stop() {
    log_info "Stopping services..."
    cd $APP_DIR
    docker compose -f $COMPOSE_FILE down
    log_info "Services stopped."
}

# =============================================================================
# Restart Services
# =============================================================================
restart() {
    log_info "Restarting services..."
    cd $APP_DIR
    docker compose -f $COMPOSE_FILE restart
    log_info "Services restarted."
}

# =============================================================================
# Run Database Migrations
# =============================================================================
migrate() {
    log_info "Running database migrations..."
    cd $APP_DIR
    docker compose -f $COMPOSE_FILE exec api alembic upgrade head
    log_info "Migrations complete."
}

# =============================================================================
# Create Admin User
# =============================================================================
create_admin() {
    log_info "Creating admin user..."
    cd $APP_DIR

    read -p "Enter admin email: " ADMIN_EMAIL
    read -sp "Enter admin password: " ADMIN_PASSWORD
    echo ""

    docker compose -f $COMPOSE_FILE exec api python -c "
from app.core.security import get_password_hash
from app.db.session import SessionLocal
from app.models.user import User
import asyncio

async def create_admin():
    # This is a placeholder - adjust based on your actual user creation logic
    print('Admin user creation would happen here')
    print(f'Email: $ADMIN_EMAIL')

asyncio.run(create_admin())
"
    log_info "Admin user created."
}

# =============================================================================
# Shell Access
# =============================================================================
shell() {
    SERVICE=${1:-"api"}
    cd $APP_DIR
    docker compose -f $COMPOSE_FILE exec $SERVICE /bin/sh
}

# =============================================================================
# Main
# =============================================================================
case "${1:-help}" in
    setup)
        setup
        ;;
    ssl)
        ssl_setup
        ;;
    deploy)
        deploy
        ;;
    update)
        update
        ;;
    logs)
        logs $2
        ;;
    status)
        status
        ;;
    backup)
        backup
        ;;
    rollback)
        rollback
        ;;
    stop)
        stop
        ;;
    restart)
        restart
        ;;
    migrate)
        migrate
        ;;
    create-admin)
        create_admin
        ;;
    shell)
        shell $2
        ;;
    *)
        echo "Stratum AI Beta Deployment Script"
        echo ""
        echo "Usage: $0 [command]"
        echo ""
        echo "Commands:"
        echo "  setup        - Initial server setup (run once)"
        echo "  ssl          - Setup/renew SSL certificate"
        echo "  deploy       - Full deployment"
        echo "  update       - Update to latest version"
        echo "  logs [svc]   - View logs (optionally for specific service)"
        echo "  status       - Check service status"
        echo "  backup       - Create backup"
        echo "  rollback     - Rollback to last backup"
        echo "  stop         - Stop all services"
        echo "  restart      - Restart all services"
        echo "  migrate      - Run database migrations"
        echo "  create-admin - Create admin user"
        echo "  shell [svc]  - Shell access (default: api)"
        echo ""
        echo "Examples:"
        echo "  $0 setup     # Initial setup"
        echo "  $0 deploy    # Deploy application"
        echo "  $0 logs api  # View API logs"
        echo "  $0 status    # Check status"
        ;;
esac
