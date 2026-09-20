from datetime import datetime, timedelta, timezone

import pytest

from app.database import get_db
from app.models import News, PageViewDaily
from main import app

EDITOR = {"Authorization": "Bearer editor-test-token-" + "x" * 32}
READER = {"Authorization": "Bearer analytics-test-token-" + "y" * 32}
ARTICLE = {"slug": "website-update", "title": "网站更新", "summary": "本次更新说明", "content": "第一段。\n第二段。"}


def test_permissions_and_disabled_configuration(client, monkeypatch):
    assert client.get("/api/admin/analytics").status_code == 401
    assert client.get("/api/admin/analytics", headers={"Authorization": "Bearer wrong"}).status_code == 401
    assert client.get("/api/admin/analytics", headers=READER).status_code == 200
    for path in ("/api/admin/news", "/api/admin/news/missing", "/api/admin/audit"):
        assert client.get(path, headers=READER).status_code == 403
    assert client.post("/api/admin/news", headers=READER, json=ARTICLE).status_code == 403
    assert client.put("/api/admin/news/missing", headers=READER, json={**ARTICLE, "expected_version": 1}).status_code == 403
    monkeypatch.delenv("SITE_ADMIN_TOKEN")
    monkeypatch.setenv("SITE_ANALYTICS_TOKEN", "short")
    assert client.get("/api/admin/analytics", headers=EDITOR).status_code == 503


def test_equal_tokens_cannot_grant_write_access_to_reader(client, monkeypatch):
    monkeypatch.setenv("SITE_ADMIN_TOKEN", "analytics-test-token-" + "y" * 32)
    assert client.get("/api/admin/analytics", headers=READER).status_code == 503


def test_news_full_lifecycle_and_version_conflicts(client):
    response = client.post("/api/admin/news", headers=EDITOR, json=ARTICLE)
    assert response.status_code == 201
    assert response.headers["cache-control"] == "no-store"
    assert response.json()["status"] == "draft"
    assert response.json()["version"] == 1
    assert client.post("/api/admin/news", headers=EDITOR, json=ARTICLE).status_code == 409
    for page in ("/", "/news", "/sitemap.xml"):
        assert "website-update" not in client.get(page).text
    assert client.get("/news/website-update").status_code == 404
    assert client.get("/api/admin/news?status=draft", headers=EDITOR).json()["total"] == 1
    content = {key: value for key, value in ARTICLE.items() if key != "slug"}
    response = client.put("/api/admin/news/website-update", headers=EDITOR,
                          json={**content, "expected_version": 1, "status": "published"})
    assert response.status_code == 200
    assert response.json()["version"] == 2
    assert response.json()["published_at"]
    for page in ("/", "/news", "/sitemap.xml"):
        assert "website-update" in client.get(page).text
    assert "第一段。" in client.get("/news/website-update").text
    response = client.put("/api/admin/news/website-update", headers=EDITOR,
                          json={**content, "expected_version": 1, "status": "draft"})
    assert response.status_code == 409
    assert client.get("/api/admin/news/website-update", headers=EDITOR).json()["status"] == "published"
    assert client.put("/api/admin/news/website-update", headers=EDITOR,
        json={**content, "expected_version": 2, "status": "draft"}).status_code == 200
    assert client.get("/news/website-update").status_code == 404
    for page in ("/", "/news", "/sitemap.xml"):
        assert "website-update" not in client.get(page).text
    assert [row["action"] for row in client.get("/api/admin/audit", headers=EDITOR).json()] == ["unpublish", "publish", "create"]


@pytest.mark.parametrize("change", [{"title": "   "}, {"slug": "../bad"}, {"status": "scheduled"}, {"source_url": "javascript:alert(1)"}, {"content": ""}])
def test_reject_invalid_content(client, change):
    assert client.post("/api/admin/news", headers=EDITOR, json={**ARTICLE, **change}).status_code == 422


def test_news_escapes_html_and_searches(client):
    payload = {**ARTICLE, "title": "<script>alert(1)</script>", "content": '<img src=x onerror="alert(1)">', "status": "published"}
    assert client.post("/api/admin/news", headers=EDITOR, json=payload).status_code == 201
    response = client.get("/news/website-update")
    assert '<img src=x onerror="alert(1)">' not in response.text
    assert "&lt;img" in response.text
    assert "website-update" in client.get("/news?q=script").text
    assert "没有找到相关新闻" in client.get("/news?q=missing").text


def test_news_pagination_and_empty_pages(client):
    assert "新闻正在准备中" in client.get("/news").text
    for i in range(10):
        client.post("/api/admin/news", headers=EDITOR, json={**ARTICLE, "slug": f"news-{i}", "status": "published"})
    assert "第 1 / 2 页" in client.get("/news").text
    assert "第 2 / 2 页" in client.get("/news?page=2").text
    assert "第 2 / 2 页" in client.get("/news?page=999").text


def test_pageview_accounting_excludes_non_pages_and_private_queries(client):
    for path in ("/", "/services", "/about", "/guide", "/news", "/tools", "/tools/text-helper"):
        assert client.get(path).status_code == 200
    client.get("/tools?q=private-search")
    client.get("/health")
    client.get("/static/site.css")
    client.get("/docs")
    client.get("/missing")
    client.get("/news/missing")
    client.get("/api/tools")
    client.get("/", headers={"User-Agent": "Googlebot"})
    client.get("/", headers={"Sec-Purpose": "prefetch"})
    client.head("/")
    data = client.get("/api/admin/analytics?days=7", headers=READER).json()
    assert data["total_views"] == 8
    assert len(data["daily"]) == 7
    assert data["daily"][-1]["views"] == 8
    assert data["daily"][0]["views"] == 0
    assert next(row["views"] for row in data["top_pages"] if row["path"] == "/tools") == 2
    assert "private-search" not in str(data)
    assert client.get("/api/admin/analytics?days=91", headers=READER).status_code == 422


def test_analytics_window_and_failure_isolation(client, monkeypatch):
    dependency = app.dependency_overrides[get_db]()
    db = next(dependency)
    today = datetime.now(timezone.utc).date()
    db.add_all([PageViewDaily(day=today-timedelta(days=1), path="/", views=3),
                PageViewDaily(day=today-timedelta(days=9), path="/", views=99)])
    db.commit()
    dependency.close()
    assert client.get("/api/admin/analytics?days=7", headers=READER).json()["total_views"] == 3
    def failing_session():
        raise RuntimeError("simulated unavailable analytics storage")
    monkeypatch.setattr("app.analytics.SessionLocal", failing_session)
    assert client.get("/about").status_code == 200


def test_sqlite_api_stats_are_separate_from_page_views(client):
    client.get("/tools")
    response = client.get("/api/stats")
    assert response.status_code == 200
    assert response.json()["total_api_calls"] == 0
    assert client.get("/api/tools/text-helper/usage").status_code == 200
