from fastapi import Request
from sqlalchemy.orm import Session
import time
from app.database import SessionLocal
from app.models import ApiLog
from app.analytics import PAGE_ROUTES, record_page_view
from starlette.concurrency import run_in_threadpool
import logging

logger = logging.getLogger(__name__)


async def log_api_call(request: Request, call_next):
    """Middleware to log API calls to database."""
    start_time = time.time()

    # Get request metadata
    endpoint = str(request.url.path)
    method = request.method
    client_ip = request.client.host if request.client else None
    user_agent = request.headers.get("user-agent")

    # Process the request
    response = await call_next(request)

    # Calculate response time
    process_time_ms = int((time.time() - start_time) * 1000)

    route_name = getattr(request.scope.get("route"), "name", "")
    is_bot = any(marker in (user_agent or "").lower() for marker in ("bot", "spider", "crawler", "headless", "healthcheck"))
    prefetch = "prefetch" in (request.headers.get("purpose", "") + request.headers.get("sec-purpose", "")).lower()
    if method == "GET" and response.status_code == 200 and route_name in PAGE_ROUTES and not is_bot and not prefetch:
        await run_in_threadpool(record_page_view, request.url.path)
    if endpoint.startswith("/api/admin/"):
        response.headers["Cache-Control"] = "no-store"

    # Only log API endpoints (skip static files and docs)
    if endpoint.startswith("/api/") and not endpoint.startswith("/api/admin/"):
        try:
            db: Session = SessionLocal()
            try:
                log_entry = ApiLog(
                    endpoint=endpoint,
                    method=method,
                    client_ip=client_ip,
                    user_agent=user_agent,
                    status_code=response.status_code,
                    response_time_ms=process_time_ms,
                )
                db.add(log_entry)
                db.commit()
            except Exception as e:
                logger.error(f"Failed to log API call: {e}")
                db.rollback()
            finally:
                db.close()
        except Exception as e:
            logger.error(f"Failed to create database session for logging: {e}")

    # Add response time header for debugging
    response.headers["X-Process-Time"] = str(process_time_ms)

    return response
