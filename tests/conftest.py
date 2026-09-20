import pytest
from fastapi.testclient import TestClient
from main import app
from app.database import Base, get_db
from app.models import Tool
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool


@pytest.fixture
def client(monkeypatch):
    """Create a test client for the FastAPI app."""
    engine = create_engine("sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool)
    Base.metadata.create_all(engine)
    factory = sessionmaker(bind=engine)
    monkeypatch.setattr("app.middleware.SessionLocal", factory)
    monkeypatch.setattr("app.analytics.SessionLocal", factory)
    monkeypatch.setenv("SITE_ADMIN_TOKEN", "editor-test-token-" + "x" * 32)
    monkeypatch.setenv("SITE_ANALYTICS_TOKEN", "analytics-test-token-" + "y" * 32)
    def test_db():
        with factory() as db:
            yield db
    app.dependency_overrides[get_db] = test_db
    with factory() as db:
        db.add_all([
            Tool(name="文本助手", slug="text-helper", description="整理文字内容", category="文本", api_endpoint="/api/text"),
            Tool(name="JSON Helper", slug="json-helper", short_description="Format JSON", category="开发"),
            Tool(name="100% 工具", slug="percent", category="开发"),
            Tool(name="隐藏工具", slug="hidden", category="内部", is_active=False),
        ])
        db.commit()
    try:
        with TestClient(app) as test_client:
            yield test_client
    finally:
        app.dependency_overrides.pop(get_db, None)
        engine.dispose()
