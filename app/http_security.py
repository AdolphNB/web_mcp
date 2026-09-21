"""Browser protections without changing page scripts or public API responses."""
import os

from starlette.datastructures import MutableHeaders
from starlette.middleware.cors import CORSMiddleware


SECURITY_HEADERS = {
    "X-Content-Type-Options": "nosniff",
    "X-Frame-Options": "SAMEORIGIN",
    "Referrer-Policy": "strict-origin-when-cross-origin",
    # No script/style restrictions yet: inline homepage styles and Swagger stay usable.
    "Content-Security-Policy": "base-uri 'self'; object-src 'none'; frame-ancestors 'self'",
}


def origins_from_env(name, default):
    return [value.strip() for value in os.getenv(name, default).split(",") if value.strip()]


class ScopedCORSMiddleware:
    def __init__(self, app):
        public_origins = origins_from_env("CORS_ORIGINS", "*")
        admin_origins = origins_from_env("SITE_ADMIN_CORS_ORIGINS", "")
        if "*" in admin_origins:
            raise ValueError("SITE_ADMIN_CORS_ORIGINS must list explicit origins")
        self.public = CORSMiddleware(
            app, allow_origins=public_origins,
            allow_credentials="*" not in public_origins,
            allow_methods=["*"], allow_headers=["*"],
        )
        self.admin = CORSMiddleware(
            app, allow_origins=admin_origins, allow_credentials=False,
            allow_methods=["GET", "POST", "PUT"],
            allow_headers=["Authorization", "Content-Type"],
        )

    async def __call__(self, scope, receive, send):
        path = scope.get("path", "")
        handler = self.admin if path == "/api/admin" or path.startswith("/api/admin/") else self.public
        await handler(scope, receive, send)


class SecurityHeadersMiddleware:
    def __init__(self, app):
        self.app = app

    async def __call__(self, scope, receive, send):
        async def secure_send(message):
            if message["type"] == "http.response.start":
                headers = MutableHeaders(scope=message)
                for name, value in SECURITY_HEADERS.items():
                    headers.setdefault(name, value)
            await send(message)

        await self.app(scope, receive, secure_send)
