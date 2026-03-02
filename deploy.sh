#!/bin/bash

# Complete deployment script for mcptools.xin
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

# UV installation path
# Use pip-installed UV to avoid snap permission issues
UV_PATH="/opt/uv/bin/uv"

# Ensure UV is installed (pip version)
if [ ! -f "$UV_PATH" ]; then
    echo_warn "UV not found at $UV_PATH. Installing via pip..."
    mkdir -p /opt/uv
    pip3 install uv --target /opt/uv --break-system-packages
fi



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
apt-get install -y python3 python3-pip nginx supervisor

# Ensure uv is installed
if ! command -v uv &> /dev/null; then
    echo_warn "uv not found. Installing..."
    curl -LsSf https://astral.sh/uv/install.sh | sh
fi

# Step 2: Create project directory and set permissions
echo_step "Setting up project directory..."
mkdir -p "$PROJECT_DIR"
mkdir -p "/var/log/${PROJECT_NAME}"
mkdir -p "/var/run/${PROJECT_NAME}"
mkdir -p "/var/www/.cache"

# Set ownership before creating venv
chown -R $DEPLOY_USER:$DEPLOY_USER "$PROJECT_DIR" "/var/log/${PROJECT_NAME}" "/var/run/${PROJECT_NAME}" "/var/www/.cache"
chmod 750 "$PROJECT_DIR"
echo_step "Setting up project directory..."
mkdir -p "$PROJECT_DIR"
mkdir -p "/var/log/${PROJECT_NAME}"
mkdir -p "/var/run/${PROJECT_NAME}"
mkdir -p "/var/www/.cache"
chown -R $DEPLOY_USER:$DEPLOY_USER "/var/log/${PROJECT_NAME}" "/var/run/${PROJECT_NAME}" "/var/www/.cache"

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
            --exclude='uv.lock'
        cd "$TARGET_DIR"
    else
        echo_error "deploy directory not found. Run this script from the project root."
        exit 1
    fi
fi


# Ensure project directory ownership after rsync
echo_info "Ensuring correct ownership..."
chown -R $DEPLOY_USER:$DEPLOY_USER "$PROJECT_DIR"

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
    sudo -u $DEPLOY_USER "$UV_PATH" venv \
        --python "$SYSTEM_PYTHON" \
        --no-managed-python \
"$PROJECT_DIR/.venv"
    echo_info "Virtual environment created successfully"
else
    echo_info "Virtual environment already exists, skipping creation"
fi

# Step 5: Install dependencies with UV
echo_step "Installing dependencies with UV..."
sudo -u $DEPLOY_USER "$UV_PATH" sync --no-dev

# Ensure gunicorn is installed (needed for production)
echo_info "Ensuring gunicorn is installed..."
sudo -u $DEPLOY_USER "$UV_PATH" pip install gunicorn

echo_info "All dependencies installed successfully"

# Step 6: Setup environment variables
echo_step "Setting up environment..."
if [ ! -f ".env" ]; then
    echo_warn ".env file not found. Creating from .env.example..."
    cp .env.example .env
fi

# Step 7: Database migration
echo_step "Running database migrations..."
# Using SQLite by default
if [ "$DATABASE_URL" = "" ] || [ "$DATABASE_URL" = "sqlite:///./mcptools.db" ]; then
    .venv/bin/python scripts/migrate.py migrate
    .venv/bin/python scripts/migrate.py seed
else
    echo_warn "Using PostgreSQL. Please ensure database is configured:"
    echo_warn "  DATABASE_URL=$DATABASE_URL"
    .venv/bin/python scripts/migrate.py migrate
fi

# Step 8: Set permissions
echo_step "Setting permissions..."
chown -R $DEPLOY_USER:$DEPLOY_USER "$PROJECT_DIR"
chmod 750 "$PROJECT_DIR"

# Step 9: Setup Nginx
echo_step "Configuring Nginx..."
./deploy/setup-nginx.sh

# Step 10: Setup Supervisor
echo_step "Configuring Supervisor..."
./deploy/setup-gunicorn.sh

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
