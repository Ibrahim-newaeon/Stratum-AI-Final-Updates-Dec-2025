#!/bin/bash
# =============================================================================
# Stratum AI - Edition Build Script
# =============================================================================
# Builds standalone deployable packages for each tier
#
# Usage:
#   ./build.sh all           # Build all editions
#   ./build.sh starter       # Build Starter only
#   ./build.sh professional  # Build Professional only
#   ./build.sh enterprise    # Build Enterprise only
# =============================================================================

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT_DIR="$(dirname "$SCRIPT_DIR")"
BUILD_DIR="$SCRIPT_DIR/dist"

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

echo_info() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

echo_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

echo_warn() {
    echo -e "${YELLOW}[WARN]${NC} $1"
}

echo_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# =============================================================================
# Build Functions
# =============================================================================

build_edition() {
    local edition=$1
    local edition_dir="$SCRIPT_DIR/$edition"
    local output_dir="$BUILD_DIR/stratum-ai-$edition"

    echo_info "Building $edition edition..."

    # Create output directory
    rm -rf "$output_dir"
    mkdir -p "$output_dir"

    # Copy edition-specific files
    cp "$edition_dir/.env.example" "$output_dir/"
    cp "$edition_dir/docker-compose.yml" "$output_dir/"
    cp "$edition_dir/README.md" "$output_dir/"

    # Copy backend (excluding __pycache__, .pyc, etc.)
    echo_info "  Copying backend..."
    rsync -a --exclude='__pycache__' \
             --exclude='*.pyc' \
             --exclude='.pytest_cache' \
             --exclude='.env' \
             --exclude='*.egg-info' \
             "$ROOT_DIR/backend/" "$output_dir/backend/"

    # Copy frontend (excluding node_modules)
    echo_info "  Copying frontend..."
    rsync -a --exclude='node_modules' \
             --exclude='dist' \
             --exclude='.env' \
             "$ROOT_DIR/frontend/" "$output_dir/frontend/"

    # Copy ML models
    echo_info "  Copying ML models..."
    mkdir -p "$output_dir/ml_service"
    cp -r "$ROOT_DIR/ml_service/models" "$output_dir/ml_service/" 2>/dev/null || true

    # Copy scripts
    echo_info "  Copying scripts..."
    cp -r "$ROOT_DIR/scripts" "$output_dir/"

    # Copy docs
    echo_info "  Copying documentation..."
    cp -r "$ROOT_DIR/docs" "$output_dir/"

    # Create version file
    echo "$edition-$(date +%Y%m%d)" > "$output_dir/VERSION"

    # Create quick start script
    cat > "$output_dir/start.sh" << 'EOF'
#!/bin/bash
# Quick start script for Stratum AI

if [ ! -f .env ]; then
    echo "Creating .env from .env.example..."
    cp .env.example .env
    echo "Please edit .env with your configuration, then run this script again."
    exit 1
fi

echo "Starting Stratum AI..."
docker compose up -d

echo ""
echo "Stratum AI is starting..."
echo "Frontend: http://localhost:5173"
echo "API Docs: http://localhost:8000/docs"
echo ""
echo "To view logs: docker compose logs -f"
EOF
    chmod +x "$output_dir/start.sh"

    # Create stop script
    cat > "$output_dir/stop.sh" << 'EOF'
#!/bin/bash
echo "Stopping Stratum AI..."
docker compose down
EOF
    chmod +x "$output_dir/stop.sh"

    # Create archive
    echo_info "  Creating archive..."
    cd "$BUILD_DIR"
    tar -czf "stratum-ai-$edition.tar.gz" "stratum-ai-$edition"

    # Calculate size
    local size=$(du -h "stratum-ai-$edition.tar.gz" | cut -f1)

    echo_success "$edition edition built: stratum-ai-$edition.tar.gz ($size)"
}

build_all() {
    echo_info "Building all editions..."
    echo ""

    build_edition "starter"
    echo ""

    build_edition "professional"
    echo ""

    build_edition "enterprise"
    echo ""

    echo_success "All editions built successfully!"
    echo ""
    echo "Output files:"
    ls -lh "$BUILD_DIR"/*.tar.gz
}

# =============================================================================
# Main
# =============================================================================

# Create build directory
mkdir -p "$BUILD_DIR"

case "${1:-all}" in
    starter)
        build_edition "starter"
        ;;
    professional)
        build_edition "professional"
        ;;
    enterprise)
        build_edition "enterprise"
        ;;
    all)
        build_all
        ;;
    clean)
        echo_info "Cleaning build directory..."
        rm -rf "$BUILD_DIR"
        echo_success "Build directory cleaned"
        ;;
    *)
        echo "Usage: $0 {starter|professional|enterprise|all|clean}"
        exit 1
        ;;
esac
