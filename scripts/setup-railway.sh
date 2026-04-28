#!/usr/bin/env bash
# Stratum AI Railway Setup Script (Bash)
# Run from the project root directory

set -euo pipefail

PROJECT_NAME="${1:-stratum-ai2}"
DRY_RUN="${DRY_RUN:-false}"
SKIP_DEPLOY="${SKIP_DEPLOY:-false}"

G="\033[32m"; Y="\033[33m"; R="\033[31m"; C="\033[36m"; B="\033[1m"; X="\033[0m"

info()  { echo -e "${C}[INFO]${X}  $*"; }
ok()    { echo -e "${G}[OK]${X}    $*"; }
warn()  { echo -e "${Y}[WARN]${X}  $*"; }
err()   { echo -e "${R}[ERR]${X}   $*"; }
step()  { echo -e "\n${B}$*${X}\n$(printf '=%.0s' $(seq 1 ${#1}))"; }

run_railway() {
    if [[ "$DRY_RUN" == "true" ]]; then
        echo -e "${Y}[DRY]${X}  railway $*"
        return 0
    fi
    railway "$@"
}

new_secret() {
    openssl rand -hex 32
}

get_git_remote() {
    git remote get-url origin 2>/dev/null | sed -n 's/.*github.com[:/]\([^/]*\)\/\([^/]*\).*/\1\/\2/p'
}

# ─── 1. Prerequisites ─────────────────────────────────────────────────────────
step "1. Prerequisites"

info "Checking Railway CLI..."
if ! command -v railway &> /dev/null; then
    err "Railway CLI not found. Install: npm i -g @railway/cli"
    exit 1
fi
ok "Railway CLI: $(railway --version)"

info "Checking login..."
if ! railway whoami &>/dev/null; then
    err "Not logged in. Run: railway login"
    exit 1
fi
ok "Logged in as $(railway whoami --json 2>/dev/null | jq -r '.email')"

info "Checking project root..."
if [[ ! -f "backend/Dockerfile" ]] || [[ ! -f "frontend/Dockerfile" ]]; then
    err "Not in project root. Run this from the Stratum AI repo root."
    exit 1
fi
ok "Project root confirmed"

REPO=$(get_git_remote)
[[ -n "$REPO" ]] && ok "GitHub repo: $REPO" || warn "Could not detect GitHub repo"

# ─── 2. Project ───────────────────────────────────────────────────────────────
step "2. Railway Project"

if [[ -d ".railway" ]]; then
    warn ".railway/ already exists"
    ok "Using existing project"
else
    info "Creating project '$PROJECT_NAME'..."
    run_railway init --name "$PROJECT_NAME"
    ok "Project created"
fi

# ─── 3. Services ──────────────────────────────────────────────────────────────
step "3. Services"

if ! railway service status --json 2>/dev/null | jq -e '.[] | select(.name == "backend")' &>/dev/null; then
    info "Creating backend service..."
    run_railway add --service backend
    ok "Backend service created"
else
    ok "Backend service already exists"
fi

if ! railway service status --json 2>/dev/null | jq -e '.[] | select(.name == "frontend")' &>/dev/null; then
    info "Creating frontend service..."
    run_railway add --service frontend
    ok "Frontend service created"
else
    ok "Frontend service already exists"
fi

# ─── 4. Domains ───────────────────────────────────────────────────────────────
step "4. Domains"

info "Generating backend domain..."
BACKEND_DOMAIN=$(run_railway domain --service backend 2>/dev/null | grep -oE '[a-z0-9\-]+\.up\.railway\.app' | head -1 || true)
if [[ -z "$BACKEND_DOMAIN" ]]; then
    warn "Could not auto-detect backend domain"
    BACKEND_DOMAIN="YOUR_BACKEND_DOMAIN.up.railway.app"
fi
BACKEND_URL="https://${BACKEND_DOMAIN}/api/v1"
ok "Backend domain: $BACKEND_DOMAIN"

info "Generating frontend domain..."
FRONTEND_DOMAIN=$(run_railway domain --service frontend 2>/dev/null | grep -oE '[a-z0-9\-]+\.up\.railway\.app' | head -1 || true)
if [[ -z "$FRONTEND_DOMAIN" ]]; then
    warn "Could not auto-detect frontend domain"
    FRONTEND_DOMAIN="YOUR_FRONTEND_DOMAIN.up.railway.app"
fi
FRONTEND_URL="https://${FRONTEND_DOMAIN}"
ok "Frontend domain: $FRONTEND_DOMAIN"

# ─── 5. Databases ─────────────────────────────────────────────────────────────
step "5. Databases"

info "Adding PostgreSQL..."
run_railway add --database postgres --service backend || true
ok "PostgreSQL added"

info "Adding Redis..."
run_railway add --database redis --service backend || true
ok "Redis added"

# ─── 6. Secrets ───────────────────────────────────────────────────────────────
step "6. Secrets"

SECRET_KEY=$(new_secret)
JWT_SECRET=$(new_secret)
PII_KEY=$(new_secret)
ok "Secrets generated"

# ─── 7. Backend Variables ─────────────────────────────────────────────────────
step "7. Backend Environment Variables"

declare -A BACKEND_VARS=(
    [APP_ENV]=production
    [DEBUG]=false
    [SECRET_KEY]="$SECRET_KEY"
    [JWT_SECRET_KEY]="$JWT_SECRET"
    [PII_ENCRYPTION_KEY]="$PII_KEY"
    [LOG_LEVEL]=INFO
    [LOG_FORMAT]=json
    [CORS_ORIGINS]="$FRONTEND_URL"
    [FRONTEND_URL]="$FRONTEND_URL"
    [ENABLE_WHATSAPP]=false
    [USE_MOCK_AD_DATA]=true
    [MARKET_INTEL_PROVIDER]=mock
)

for key in "${!BACKEND_VARS[@]}"; do
    info "Setting $key..."
    run_railway variable set --service backend --skip-deploys "$key=${BACKEND_VARS[$key]}"
done
ok "Backend variables set"

# ─── 8. Frontend Variables ────────────────────────────────────────────────────
step "8. Frontend Environment Variables"

declare -A FRONTEND_VARS=(
    [VITE_API_URL]="$BACKEND_URL"
    [VITE_WS_URL]="wss://${BACKEND_DOMAIN}"
    [VITE_DEFAULT_LOCALE]=en
)

for key in "${!FRONTEND_VARS[@]}"; do
    info "Setting $key..."
    run_railway variable set --service frontend --skip-deploys "$key=${FRONTEND_VARS[$key]}"
done
ok "Frontend variables set"

# ─── 9. Deploy ────────────────────────────────────────────────────────────────
step "9. Deploy"

if [[ "$SKIP_DEPLOY" == "true" ]]; then
    warn "Skipping deployment"
else
    info "Deploying backend..."
    run_railway up backend/ --service backend --path-as-root
    ok "Backend deployed"

    info "Deploying frontend..."
    run_railway up frontend/ --service frontend --path-as-root
    ok "Frontend deployed"
fi

# ─── Summary ──────────────────────────────────────────────────────────────────
step "Summary"

cat <<EOF
${G}Setup complete!${X}

Project:     $PROJECT_NAME
Backend:     https://$BACKEND_DOMAIN
Frontend:    https://$FRONTEND_DOMAIN

Healthchecks:
  Backend:   https://$BACKEND_DOMAIN/health
  Frontend:  https://$FRONTEND_DOMAIN

Commands:
  railway logs --service backend
  railway logs --service frontend
  railway open

If domains were placeholders, update after deploy:
  railway variable set --service frontend VITE_API_URL=https://<REAL_DOMAIN>/api/v1
EOF
