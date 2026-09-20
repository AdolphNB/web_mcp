def test_read_root(client):
    """Test the root endpoint."""
    response = client.get("/")
    assert response.status_code == 200
    assert "text/html" in response.headers["content-type"]
    assert 'id="services"' in response.text
    assert 'href="/about"' in response.text
    assert 'href="mailto:304633698@qq.com"' in response.text
    assert 'href="/static/tailwind.css"' in response.text
    assert "cdn.tailwindcss.com" not in response.text


def test_tool_catalog_only_lists_active_tools(client):
    response = client.get("/tools")
    assert response.status_code == 200
    assert "共 3 个工具" in response.text
    assert "隐藏工具" not in response.text
    assert '<option value="内部"' not in response.text


def test_search_and_category_filters_combine(client):
    response = client.get("/tools", params={"q": " json ", "category": "开发"})
    assert "找到 1 个结果" in response.text
    assert 'href="/tools/json-helper"' in response.text
    assert 'href="/tools/text-helper"' not in response.text
    assert 'value="json"' in response.text
    assert "没有找到匹配的工具" in client.get("/tools?q=json&category=文本").text


def test_search_matches_descriptions_and_literal_wildcards(client):
    assert "找到 1 个结果" in client.get("/tools", params={"q": "文字"}).text
    assert "找到 1 个结果" in client.get("/tools", params={"q": "%"}).text
    assert "找到 0 个结果" in client.get("/tools", params={"q": "_"}).text


def test_search_input_is_escaped(client):
    response = client.get("/tools", params={"q": '<script>alert("x")</script>'})
    assert '<script>alert("x")</script>' not in response.text
    assert "&lt;script&gt;" in response.text


def test_detail_and_hidden_tool(client):
    response = client.get("/tools/text-helper")
    assert response.status_code == 200
    assert 'id="api-endpoint"' in response.text
    assert "/api/text" in response.text
    assert client.get("/tools/hidden").status_code == 404


def test_html_404_and_api_json_404(client):
    response = client.get("/missing", headers={"accept": "text/html"})
    assert response.status_code == 404
    assert "返回首页" in response.text
    response = client.get("/api/tools/missing", headers={"accept": "text/html"})
    assert response.status_code == 404
    assert response.json() == {"detail": "Tool not found"}
