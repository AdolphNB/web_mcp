#!/bin/bash
# acme.sh manual-auth-hook for Volcengine DNS
exec /root/web_mcp/scripts/dns_volc_hook.py add "$CERTBOT_DOMAIN" "$CERTBOT_VALIDATION"
