#!/bin/bash

# Complete deployment script for mcptools.xin
# This script handles the entire deployment process

set -e

PROJECT_NAME="mcptools"
PROJECT_DIR="/var/www/mcptools"
DEPLOY_USER="www-data"

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
apt-get install -y python3 python3-venv python3-pip nginx supervisor

# Step 2: Create project directory
echo_step "Setting up project directory..."
mkdir -p "$PROJECT_DIR"
mkdir -p "/var/log/${PROJECT_NAME}"
mkdir -p "/var/run/${PROJECT_NAME}"

# Step 3: Copy application files
echo_step "Copying application files..."
if [ -d "deploy" ]; then
    cp -r . "$PROJECT_DIR/"
    cd "$PROJECT_DIR"
else
    echo_error "deploy directory not found. Run this script from the project root."
    exit 1
fi

# Step 4: Create virtual environment
echo_step "Creating Python virtual environment..."
python3 -m venv .venv
.venv/bin/pip install --upgrade pip
.venv/bin/pip install -r requirements.txt
.venv/bin/pip install gunicorn

# Step 5: Setup environment variables
echo_step "Setting up environment..."
if [ ! -f ".env" ]; then
    echo_warn ".env file not found. Creating from .env.example..."
    cp .env.example .env
fi

# Step 6: Database migration
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

# Step 7: Set permissions
echo_step "Setting permissions..."
chown -R $DEPLOY_USER:$DEPLOY_USER "$PROJECT_DIR"
chmod 750 "$PROJECT_DIR"

# Step 8: Setup Nginx
echo_step "Configuring Nginx..."
./deploy/setup-nginx.sh

# Step 9: Setup Supervisor
echo_step "Configuring Supervisor..."
./deploy/setup-gunicorn.sh

# Step 10: Start services
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
