#!/bin/bash

# Gunicorn and Supervisor setup script for mcptools.xin
# Uses UV for environment management

set -e

PROJECT_NAME="mcptools"
DEPLOY_USER="www-data"
PROJECT_DIR="/var/www/mcptools"
VENV_DIR="${PROJECT_DIR}/.venv"
SUPERVISOR_CONF="/etc/supervisor/conf.d/${PROJECT_NAME}.conf"
LOG_DIR="/var/log/mcptools"
PID_DIR="/var/run/mcptools"

# UV installation path (using pip-installed UV to avoid snap issues)
UV_PATH="/opt/uv/bin/uv"


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

echo_info "Setting up Gunicorn and Supervisor for ${PROJECT_NAME}..."

# Create necessary directories
echo_info "Creating directories..."
mkdir -p "$LOG_DIR" "$PID_DIR"
chown -R www-data:www-data "$LOG_DIR" "$PID_DIR" "/var/www/.cache"

# Install required packages
echo_info "Installing required packages..."
apt-get update
apt-get install -y supervisor

# Setup virtual environment verification
echo_info "Verifying virtual environment..."
if [ ! -d "$VENV_DIR" ]; then
    echo_error "Virtual environment not found at $VENV_DIR"
    echo_error "Please run deploy.sh first to create the virtual environment"
    exit 1
fi

# Verify permissions
echo_info "Verifying virtual environment permissions..."
chown -R $DEPLOY_USER:$DEPLOY_USER "$VENV_DIR"
chmod -R 755 "$VENV_DIR"

# Verify UV and Python in venv
if ! sudo -u $DEPLOY_USER "$VENV_DIR/bin/python" --version &> /dev/null; then
    echo_error "Python in venv is not executable by $DEPLOY_USER"
    exit 1
fi

# Verify gunicorn is installed
if [ ! -f "$VENV_DIR/bin/gunicorn" ]; then
    echo_info "Installing gunicorn..."
    sudo -u $DEPLOY_USER "$UV_PATH" pip install gunicorn uvicorn[standard]
fi

echo_info "Virtual environment is ready"

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
