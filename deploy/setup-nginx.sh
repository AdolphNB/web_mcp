#!/bin/bash

# Nginx deployment helper script for mcptools.xin

set -e

PROJECT_NAME="mcptools"
NGINX_CONF="/etc/nginx/sites-available/${PROJECT_NAME}"
NGINX_LINK="/etc/nginx/sites-enabled/${PROJECT_NAME}"
PROJECT_DIR="/var/www/mcptools"

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

echo_info "Installing Nginx configuration for ${PROJECT_NAME}..."

# Backup existing config if it exists
if [ -f "$NGINX_CONF" ]; then
    echo_warn "Backing up existing configuration..."
    cp "$NGINX_CONF" "${NGINX_CONF}.backup.$(date +%Y%m%d_%H%M%S)"
fi

# Copy the configuration
echo_info "Copying nginx.conf to ${NGINX_CONF}"
cp "$PROJECT_DIR/deploy/nginx.conf" "$NGINX_CONF"

# Enable the site
echo_info "Enabling site..."
ln -sf "$NGINX_CONF" "$NGINX_LINK"

# Test configuration
echo_info "Testing Nginx configuration..."
if nginx -t; then
    echo_info "Nginx configuration is valid"
else
    echo_error "Nginx configuration test failed"
    exit 1
fi

# Reload Nginx
echo_info "Reloading Nginx..."
systemctl reload nginx

echo_info "Nginx configuration deployed successfully!"
echo ""
echo_info "Next steps:"
echo "  1. Ensure your FastAPI application is running:"
echo "     systemctl start mcptools"
echo ""
echo "  2. To setup SSL (HTTPS), use certbot:"
echo "     sudo apt install certbot python3-certbot-nginx"
echo "     sudo certbot --nginx -d mcptools.xin"
