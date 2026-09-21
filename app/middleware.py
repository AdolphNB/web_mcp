from fastapi import Request
import time
from app.database import SessionLocal
from app.models import ApiLog
from app.analytics import PAGE_ROUTES, record_page_view
from starlette.concurrency import run_in_threadpool
import logging

logger = logging.getLogger(__name__)


def record_api_call(**values):
    """Use a worker thread for synchronous SQLAlchemy; preserve existing metrics."""
    try:
        with SessionLocal() as db:
            db.add(ApiLog(**values))
            db.commit()
    except Exception:
        # Do not print DB parameters (which may include IPs and request headers).
        logger.error("Failed to record API call")


async def log_api_call(request: Request, call_next):
    """Middleware to log API calls to database."""
    start_time = time.perf_counter()

    # Get request metadata
    endpoint = str(request.url.path)
    method = request.method
    client_ip = request.client.host if request.client else None
    user_agent = request.headers.get("user-agent")

    # Process the request
    response = await call_next(request)

    # Calculate response time
    process_time_ms = int((time.perf_counter() - start_time) * 1000)

    route_name = getattr(request.scope.get("route"), "name", "")
    is_bot = any(marker in (user_agent or "").lower() for marker in ("bot", "spider", "crawler", "headless", "healthcheck"))
    prefetch = "prefetch" in (request.headers.get("purpose", "") + request.headers.get("sec-purpose", "")).lower()
    if method == "GET" and response.status_code == 200 and route_name in PAGE_ROUTES and not is_bot and not prefetch:
        await run_in_threadpool(record_page_view, request.url.path)
    if endpoint.startswith(("/api/admin/", "/api/support/")):
        response.headers["Cache-Control"] = "no-store"

    # Only log API endpoints (skip static files and docs)
    if endpoint.startswith("/api/") and not endpoint.startswith(("/api/admin/", "/api/support/")):
        await run_in_threadpool(
            record_api_call,
            endpoint=endpoint[:255], method=method[:10],
            client_ip=client_ip[:45] if client_ip else None,
            user_agent=user_agent[:500] if user_agent else None,
            status_code=response.status_code, response_time_ms=process_time_ms,
        )

    # Add response time header for debugging
    response.headers["X-Process-Time"] = str(process_time_ms)

    return response
