"""
测试 fixtures — 提供 mock 数据和依赖注入
"""

import os
from unittest.mock import MagicMock, patch

import pytest


@pytest.fixture
def mock_newsapi_key():
    """注入测试用 API Key"""
    with patch.dict(os.environ, {"NEWS_API_KEY": "test-key-12345"}):
        yield


@pytest.fixture
def sample_article_raw():
    """NewsAPI 返回的单条文章原始数据"""
    return {
        "title": "Lithium Prices Surge Amid EV Demand",
        "url": "https://example.com/lithium-surge",
        "description": "Lithium prices have risen sharply...",
        "publishedAt": "2026-06-01T12:00:00Z",
        "source": {"name": "Mining Weekly"},
    }


@pytest.fixture
def sample_newsapi_response(sample_article_raw):
    """NewsAPI get_everything 标准响应"""
    return {
        "status": "ok",
        "totalResults": 1,
        "articles": [sample_article_raw],
    }


@pytest.fixture
def sample_html():
    """测试用 HTML 页面"""
    return """<!DOCTYPE html>
<html>
<head><title>Test Article</title></head>
<body>
    <header>Site Header</header>
    <nav>Navigation</nav>
    <script>console.log('remove me')</script>
    <style>.ad { display: none }</style>
    <article>
        <p>First paragraph of the article.</p>
        <p>Second paragraph with more details.</p>
        <p>Third concluding paragraph.</p>
    </article>
    <footer>Site Footer</footer>
</body>
</html>"""
