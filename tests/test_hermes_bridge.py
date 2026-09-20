"""Run with the optional integrations/hermes/requirements.txt installed."""
import httpx
import pytest

pytest.importorskip("mcp")
from integrations.hermes import server


@pytest.fixture
def bridge(client, monkeypatch):
    original_client = httpx.Client
    def handle(request):
        response = client.request(request.method, request.url.raw_path.decode(),
            headers=dict(request.headers), content=request.content)
        return httpx.Response(response.status_code, headers=response.headers, content=response.content)
    monkeypatch.setenv("SITE_API_URL", "https://example.test")
    monkeypatch.setenv("SITE_API_TOKEN", "editor-test-token-" + "x" * 32)
    monkeypatch.delenv("SITE_API_TOKEN_FILE", raising=False)
    monkeypatch.setattr(server.httpx, "Client", lambda **kwargs: original_client(transport=httpx.MockTransport(handle), **kwargs))
    return server


def test_bridge_can_manage_news_and_read_stats(bridge):
    draft = bridge.create_news_draft("agent-news", "Agent 测试", "摘要", "正文")
    assert draft["status"] == "draft"
    assert bridge.list_site_news("draft")["total"] == 1
    assert bridge.get_site_news("agent-news")["version"] == 1
    published = bridge.update_site_news("agent-news", 1, "Agent 测试", "摘要", "正文", "published")
    assert published["status"] == "published"
    with pytest.raises(RuntimeError, match="409"):
        bridge.update_site_news("agent-news", 1, "旧内容", "摘要", "正文", "draft")
    assert bridge.get_site_analytics(7)["metric"] == "page_views"


def test_bridge_requires_https_and_safe_slugs(bridge, monkeypatch):
    with pytest.raises(ValueError):
        bridge.get_site_news("../../analytics")
    monkeypatch.setenv("SITE_API_URL", "http://example.test")
    with pytest.raises(ValueError, match="HTTPS"):
        bridge.get_site_analytics()


@pytest.mark.asyncio
async def test_mcp_tool_discovery():
    tools = await server.mcp.list_tools()
    assert {tool.name for tool in tools} == {"get_site_analytics", "list_site_news", "get_site_news", "create_news_draft", "update_site_news"}
    assert next(tool for tool in tools if tool.name == "get_site_analytics").annotations.readOnlyHint
