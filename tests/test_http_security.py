import threading

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.database import get_db
from app.http_security import ScopedCORSMiddleware
from app.models import ApiLog
from main import app


@pytest.mark.parametrize("path", ["/", "/tools", "/docs", "/openapi.json", "/static/site.css", "/api/tools", "/missing"])
def test_security_headers_preserve_existing_responses(client, path):
    response = client.get(path)
    assert response.status_code == (404 if path == "/missing" else 200)
    assert response.headers["x-content-type-options"] == "nosniff"
    assert response.headers["x-frame-options"] == "SAMEORIGIN"
    assert "frame-ancestors 'self'" in response.headers["content-security-policy"]
    # Avoid breaking the existing inline styles and interactive API docs.
    assert "script-src" not in response.headers["content-security-policy"]


def cors_client(monkeypatch, origins=""):
    monkeypatch.setenv("CORS_ORIGINS", "*")
    monkeypatch.setenv("SITE_ADMIN_CORS_ORIGINS", origins)
    test_app = FastAPI()
    test_app.add_middleware(ScopedCORSMiddleware)
    @test_app.get("/api/tools")
    def public():
        return {"items": []}
    return TestClient(test_app)


def test_public_cors_still_works_without_credentials(monkeypatch):
    with cors_client(monkeypatch) as client:
        response = client.get("/api/tools", headers={"Origin": "https://external.example"})
        assert response.status_code == 200
        assert response.headers["access-control-allow-origin"] == "*"
        assert "access-control-allow-credentials" not in response.headers


def test_admin_cors_only_allows_explicit_origins(monkeypatch):
    with cors_client(monkeypatch, "https://admin.example") as client:
        for origin, status in [("https://admin.example", 200), ("https://external.example", 400)]:
            response = client.options("/api/admin/news", headers={
                "Origin": origin, "Access-Control-Request-Method": "PUT",
                "Access-Control-Request-Headers": "authorization,content-type",
            })
            assert response.status_code == status
            assert response.headers.get("access-control-allow-origin") == (origin if status == 200 else None)


def test_admin_cors_rejects_wildcards(monkeypatch):
    with pytest.raises(ValueError, match="explicit origins"):
        with cors_client(monkeypatch, "*"):
            pass


def test_api_logging_runs_off_event_loop_and_bounds_untrusted_fields(client, monkeypatch):
    import app.middleware as middleware
    original = middleware.record_api_call
    event_thread, log_thread = [], []
    original_clock = middleware.time.perf_counter
    def track_clock():
        event_thread.append(threading.get_ident())
        return original_clock()
    def track_log(**values):
        log_thread.append(threading.get_ident())
        return original(**values)
    monkeypatch.setattr(middleware.time, "perf_counter", track_clock)
    monkeypatch.setattr(middleware, "record_api_call", track_log)
    response = client.get("/api/" + "x" * 300, headers={"User-Agent": "a" * 1000})
    assert response.status_code == 404
    assert log_thread[0] != event_thread[0]
    dependency = app.dependency_overrides[get_db]()
    try:
        db = next(dependency)
        row = db.query(ApiLog).one()
        assert len(row.endpoint) == 255
        assert len(row.user_agent) == 500
        assert row.status_code == 404
    finally:
        dependency.close()


def test_log_failure_does_not_break_public_api_or_leak_details(client, monkeypatch, caplog):
    def fail():
        raise RuntimeError("private-log-value")
    monkeypatch.setattr("app.middleware.SessionLocal", fail)
    assert client.get("/api/tools").status_code == 200
    assert "Failed to record API call" in caplog.text
    assert "private-log-value" not in caplog.text


def test_unhandled_errors_have_safe_headers(monkeypatch):
    test_app = FastAPI()
    from main import global_exception_handler
    test_app.add_exception_handler(Exception, global_exception_handler)
    @test_app.get("/fail")
    def fail():
        raise RuntimeError("private-error")
    with TestClient(test_app, raise_server_exceptions=False) as client:
        response = client.get("/fail")
        assert response.status_code == 500
        assert response.json() == {"detail": "Internal Server Error"}
        assert response.headers["x-content-type-options"] == "nosniff"
