"""
测试 tools.py — search_news / fetch_article_content
"""

from unittest.mock import AsyncMock, patch

import httpx
import pytest

from mining_news_mcp.tools import fetch_article_content, search_news


class TestSearchNews:
    """search_news"""

    def test_returns_articles_on_success(self, mock_newsapi_key, sample_newsapi_response):
        import newsapi

        original = newsapi.NewsApiClient.get_everything
        newsapi.NewsApiClient.get_everything = lambda self, **kw: sample_newsapi_response
        try:
            results = search_news("lithium", days=7)

            assert isinstance(results, list)
            assert len(results) == 1
            assert results[0]["title"] == "Lithium Prices Surge Amid EV Demand"
            assert results[0]["url"] == "https://example.com/lithium-surge"
            assert results[0]["source"] == "Mining Weekly"
        finally:
            newsapi.NewsApiClient.get_everything = original

    def test_returns_error_when_no_api_key(self):
        with pytest.MonkeyPatch.context() as mp:
            mp.delenv("NEWS_API_KEY", raising=False)
            results = search_news("lithium")
            assert len(results) == 1
            assert "error" in results[0]

    def test_returns_error_on_api_failure(self, mock_newsapi_key):
        import newsapi

        original = newsapi.NewsApiClient.get_everything
        newsapi.NewsApiClient.get_everything = lambda self, **kw: {
            "status": "error",
            "message": "rate limited",
        }
        try:
            results = search_news("lithium")
            assert len(results) == 1
            assert "error" in results[0]
            assert "rate limited" in results[0]["error"]
        finally:
            newsapi.NewsApiClient.get_everything = original


class TestFetchArticle:
    """fetch_article_content"""

    @pytest.mark.asyncio
    async def test_extracts_paragraphs(self, sample_html):
        mock_resp = AsyncMock()
        mock_resp.text = sample_html
        mock_resp.status_code = 200
        mock_resp.raise_for_status = lambda: None

        with patch.object(httpx.AsyncClient, "get", return_value=mock_resp):
            result = await fetch_article_content("https://example.com/article")

            assert "First paragraph" in result
            assert "Second paragraph" in result
            assert "Third concluding paragraph" in result
            # script/style/nav/header/footer 应被移除
            assert "console.log" not in result
            assert "Site Header" not in result
            assert "Site Footer" not in result

    @pytest.mark.asyncio
    async def test_rejects_invalid_url(self):
        result = await fetch_article_content("not-a-url")
        assert result.startswith("Error:")

        result = await fetch_article_content("")
        assert result.startswith("Error:")

    @pytest.mark.asyncio
    async def test_handles_http_error(self):
        mock_resp = AsyncMock()
        mock_resp.status_code = 404
        mock_resp.raise_for_status = lambda: (_ for _ in ()).throw(
            httpx.HTTPStatusError("Not Found", request=object(), response=mock_resp)
        )

        with patch.object(httpx.AsyncClient, "get", return_value=mock_resp):
            result = await fetch_article_content("https://example.com/404")
            assert result.startswith("Failed to fetch article: HTTP 404")

    @pytest.mark.asyncio
    async def test_handles_timeout(self):
        async def _raise_timeout(*args, **kwargs):
            raise httpx.TimeoutException("timeout")

        with patch.object(httpx.AsyncClient, "get", side_effect=_raise_timeout):
            result = await fetch_article_content("https://example.com/slow")
            assert "timeout" in result.lower()

    @pytest.mark.asyncio
    async def test_truncates_long_content(self):
        # 生成超过 5000 字符的 HTML
        long_text = "Word " * 3000
        html = f"<html><body><p>{long_text}</p></body></html>"

        mock_resp = AsyncMock()
        mock_resp.text = html
        mock_resp.status_code = 200
        mock_resp.raise_for_status = lambda: None

        with patch.object(httpx.AsyncClient, "get", return_value=mock_resp):
            result = await fetch_article_content("https://example.com/long")
            assert len(result) <= 5000
