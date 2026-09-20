"""Bearer credentials are server-side only and disabled until configured."""
import os
import secrets

from fastapi import Depends, HTTPException
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

bearer = HTTPBearer(auto_error=False)


def management_role(credentials: HTTPAuthorizationCredentials = Depends(bearer)):
    tokens = {
        "editor": os.getenv("SITE_ADMIN_TOKEN", ""),
        "analytics": os.getenv("SITE_ANALYTICS_TOKEN", ""),
    }
    tokens = {role: token for role, token in tokens.items() if len(token) >= 32}
    if len(tokens) == 2 and tokens["editor"] == tokens["analytics"]:
        raise HTTPException(503, "Editor and analytics tokens must be different")
    if not tokens:
        raise HTTPException(503, "Management API is not configured")
    supplied = credentials.credentials if credentials else ""
    for role, token in tokens.items():
        if secrets.compare_digest(supplied.encode(), token.encode()):
            return role
    raise HTTPException(401, "Invalid management token", headers={"WWW-Authenticate": "Bearer"})


def require_editor(role: str = Depends(management_role)):
    if role != "editor":
        raise HTTPException(403, "An editor token is required")
    return role
