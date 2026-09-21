#!/bin/bash

# Complete deployment script for singularitynear.com
# This script handles the entire deployment process using UV

set -e

# Parse command line arguments
REBUILD_VENV=false
if [ "$1" = "--rebuild-venv" ]; then
    REBUILD_VENV=true
    echo -e "\033[0;32m[INFO]\033[0m Rebuild venv mode enabled"
fi

PROJECT_NAME="mcptools"
PROJECT_DIR="/var/www/mcptools"
DEPLOY_USER="www-data"
SYSTEM_PYTHON="/usr/bin/python3"
DATA_DIR="/var/lib/mcptools"

# UV installation path
# Use pip-installed UV to avoid snap permission issues
UV_PATH="/opt/uv/bin/uv"

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

echo_info() { echo -e "${GREEN}[INFO]${NC} $1"; }
echo_warn() { echo -e "${YELLOW}[WARN]${NC} $1"; }
echo_error() { echo -e "${RED}[ERROR]${NC} $1"; }
echo_step() { echo -e "${BLUE}[STEP]${NC} $1"; }

# Check if running as root
if [ "$EUID" -ne 0 ]; then
    echo_error "Please run as root or with sudo"
    exit 1
fi

echo_info "========================================"
echo_info "Deploying ${PROJECT_NAME}"
echo_info "========================================"
echo ""

# Step 1: System dependencies
echo_step "Installing system dependencies..."
apt-get update
apt-get install -y python3 python3-pip nginx supervisor logrotate

# Ensure UV is installed (pip version)
if [ ! -f "$UV_PATH" ]; then
    echo_warn "UV not found at $UV_PATH. Installing via pip..."
    mkdir -p /opt/uv
    pip3 install uv --target /opt/uv --break-system-packages
fi



# Validate the certificate before interrupting a running site.
bash ./deploy/setup-nginx.sh --check-certificate

# Stop workers before moving SQLite so no writes are lost during the switch.
# Existing files in the checkout are retained for recovery.
if supervisorctl status "$PROJECT_NAME" >/dev/null 2>&1; then
    supervisorctl stop "$PROJECT_NAME"
fi

# Step 2: Create project directory and set permissions
echo_step "Setting up project directory..."
mkdir -p "$PROJECT_DIR"
mkdir -p "/var/log/${PROJECT_NAME}"
mkdir -p "/var/run/${PROJECT_NAME}"
mkdir -p "/var/www/.cache"

# Set ownership before creating venv
chown -R $DEPLOY_USER:$DEPLOY_USER "/var/log/${PROJECT_NAME}" "/var/run/${PROJECT_NAME}" "/var/www/.cache"
chown root:$DEPLOY_USER "$PROJECT_DIR"
chmod 750 "$PROJECT_DIR"

# Step 3: Copy application files
echo_step "Copying application files..."

# Get absolute paths
SOURCE_DIR="$(pwd)"
TARGET_DIR="$PROJECT_DIR"

# Check if source and target are the same directory
if [ "$(realpath "$SOURCE_DIR")" = "$(realpath "$TARGET_DIR")" ]; then
    echo_warn "Already in deployment directory. Skipping copy step."
    cd "$TARGET_DIR"
else
    if [ -d "deploy" ]; then
        # Use rsync for better incremental copying
        echo_info "Copying from $SOURCE_DIR to $TARGET_DIR"
        # Install rsync if not available
        if ! command -v rsync &> /dev/null; then
            apt-get install -y rsync > /dev/null 2>&1
        fi
        # Copy files, excluding venv and unnecessary files
        rsync -av --delete "$SOURCE_DIR/" "$TARGET_DIR/" \
            --exclude='.venv' \
            --exclude='__pycache__' \
            --exclude='*.pyc' \
            --exclude='.git' \
            --exclude='.env' \
            --exclude='*.db' \
            --exclude='*.db-*' \
            --exclude='*.sqlite' \
            --exclude='*.sqlite-*' \
            --exclude='*.sqlite3' \
            --exclude='*.sqlite3-*'
        cd "$TARGET_DIR"
    else
        echo_error "deploy directory not found. Run this script from the project root."
        exit 1
    fi
fi


# Ensure project directory ownership after rsync
echo_info "Ensuring correct ownership..."
chown -R root:$DEPLOY_USER "$PROJECT_DIR"
chmod -R u=rwX,g=rX,o= "$PROJECT_DIR"
chmod 750 "$PROJECT_DIR"

# Step 4: Create virtual environment with UV
# IMPORTANT: Use system Python to avoid symlink permission issues
echo_step "Setting up Python virtual environment with UV..."

# Remove existing venv only if --rebuild-venv flag is set
if [ "$REBUILD_VENV" = true ] && [ -d "$PROJECT_DIR/.venv" ]; then
    echo_warn "Removing existing virtual environment..."
    rm -rf "$PROJECT_DIR/.venv"
fi

# Create venv if it doesn't exist
if [ ! -d "$PROJECT_DIR/.venv" ]; then
    echo_info "Creating virtual environment with UV (using system Python: $SYSTEM_PYTHON)..."
    # Use --python to specify system Python
    # Use --no-managed-python to prevent UV from downloading or using managed Python
    "$UV_PATH" venv \
        --python "$SYSTEM_PYTHON" \
        --no-managed-python \
"$PROJECT_DIR/.venv"
    echo_info "Virtual environment created successfully"
else
    echo_info "Virtual environment already exists, skipping creation"
fi

# Step 5: Install dependencies with UV
echo_step "Installing dependencies with UV..."
"$UV_PATH" sync --locked --no-dev

echo_info "All dependencies installed successfully"

# Step 6: Setup environment variables
echo_step "Setting up environment..."
if [ ! -f ".env" ]; then
    if [ -f ".env.example" ]; then
        echo_warn ".env file not found. Creating from .env.example..."
        cp .env.example .env
    else
        echo_warn ".env file not found and no .env.example available. Creating default .env..."
        cat > .env << 'EOF'
# Database configuration
# SQLite (default): sqlite:///./mcptools.db
# PostgreSQL: postgresql://user:password@localhost:5432/mcptools
DATABASE_URL=sqlite:///./mcptools.db

# Debug mode (set to True for development)
DEBUG=False
EOF
    fi
fi

# Step 8: Set permissions
echo_step "Setting permissions..."
chown -R root:$DEPLOY_USER "$PROJECT_DIR"
chmod -R u=rwX,g=rX,o= "$PROJECT_DIR"
chmod 750 "$PROJECT_DIR"

install -d -o "$DEPLOY_USER" -g "$DEPLOY_USER" -m 750 "$DATA_DIR"
.venv/bin/python scripts/prepare_sqlite.py --project "$PROJECT_DIR" --data-dir "$DATA_DIR"
chown -R "$DEPLOY_USER:$DEPLOY_USER" "$DATA_DIR"
chmod -R u=rwX,g=,o= "$DATA_DIR"
chown root:$DEPLOY_USER .env
chmod 640 .env
# python-dotenv parses .env in the application. Never source it as root.
echo_step "Running database migrations..."
sudo -u "$DEPLOY_USER" .venv/bin/python scripts/migrate.py migrate

# Step 9: Setup Nginx
echo_step "Configuring Nginx..."
bash ./deploy/setup-nginx.sh

# Step 10: Setup Supervisor
echo_step "Configuring Supervisor..."
bash ./deploy/setup-gunicorn.sh
install -o root -g root -m 644 deploy/logrotate.conf /etc/logrotate.d/mcptools

# Step 11: Start services
echo_step "Starting services..."
supervisorctl start $PROJECT_NAME

echo_info "========================================"
echo_info "Deployment completed successfully!"
echo_info "========================================"
echo ""
echo_info "Access your site:"
echo_info "  http://localhost"
echo ""
echo_info "Manage services:"
echo_info "  sudo supervisorctl status ${PROJECT_NAME}"
echo_info "  sudo supervisorctl restart ${PROJECT_NAME}"
echo ""
echo_info "View logs:"
echo_info "  sudo tail -f /var/log/${PROJECT_NAME}/supervisor.log"
echo_info "  sudo tail -f /var/log/nginx/${PROJECT_NAME}-access.log"
echo ""
