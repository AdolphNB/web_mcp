from fastapi import Request
from sqlalchemy.orm import Session
import time
from app.database import SessionLocal
from app.models import ApiLog
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

    # Only log API endpoints (skip static files and docs)
    if endpoint.startswith("/api/") or endpoint.startswith("/tools"):
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
