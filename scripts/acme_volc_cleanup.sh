#!/bin/bash
# acme.sh manual-cleanup-hook for Volcengine DNS
exec /root/web_mcp/scripts/dns_volc_hook.py remove "$CERTBOT_DOMAIN" "$CERTBOT_VALIDATION"
