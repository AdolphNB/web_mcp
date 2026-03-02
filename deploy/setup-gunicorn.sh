#!/bin/bash

# Gunicorn and Supervisor setup script for mcptools.xin

set -e

PROJECT_NAME="mcptools"
PROJECT_DIR="/var/www/mcptools"
VENV_DIR="${PROJECT_DIR}/.venv"
SUPERVISOR_CONF="/etc/supervisor/conf.d/${PROJECT_NAME}.conf"
LOG_DIR="/var/log/mcptools"
PID_DIR="/var/run/mcptools"

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

echo_info() {
    echo -e "${GREEN}[INFO]${NC} $1"
}

echo_warn() {
    echo -e "${YELLOW}[WARN]${NC} $1"
}

echo_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# Check if running as root
if [ "$EUID" -ne 0 ]; then
    echo_error "Please run as root or with sudo"
    exit 1
fi

echo_info "Setting up Gunicorn and Supervisor for ${PROJECT_NAME}..."

# Create necessary directories
echo_info "Creating directories..."
mkdir -p "$LOG_DIR" "$PID_DIR"
chown -R www-data:www-data "$LOG_DIR" "$PID_DIR"

# Install required packages
echo_info "Installing required packages..."
apt-get update
apt-get install -y supervisor

# Setup virtual environment if not exists
if [ ! -d "$VENV_DIR" ]; then
    echo_info "Creating virtual environment..."
    python3 -m venv "$VENV_DIR"
fi

# Install dependencies
echo_info "Installing Python dependencies..."
$VENV_DIR/bin/pip install --upgrade pip
$VENV_DIR/bin/pip install -r "$PROJECT_DIR/requirements.txt"

# Copy Supervisor configuration
echo_info "Copying Supervisor configuration..."
cp "$PROJECT_DIR/deploy/supervisor.conf" "$SUPERVISOR_CONF"

# Reload Supervisor
echo_info "Reloading Supervisor configuration..."
supervisorctl reread
supervisorctl update

echo_info "Setup completed successfully!"
echo ""
echo_info "Start the service:"
echo "  sudo supervisorctl start ${PROJECT_NAME}"
echo ""
echo_info "Check service status:"
echo "  sudo supervisorctl status ${PROJECT_NAME}"
echo ""
echo_info "View logs:"
echo "  sudo tail -f $LOG_DIR/supervisor.log"
