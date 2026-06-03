"""
测试 news_api.py — MiningNewsClient
"""

import os

import pytest

from mining_news_mcp.news_api import Article, MiningNewsClient, SearchResult


class TestArticle:
    """Article 数据类"""

    def test_from_api_parses_all_fields(self, sample_article_raw):
        article = Article.from_api(sample_article_raw)

        assert article.title == "Lithium Prices Surge Amid EV Demand"
        assert article.url == "https://example.com/lithium-surge"
        assert article.description == "Lithium prices have risen sharply..."
        assert article.published_at == "2026-06-01T12:00:00Z"
        assert article.source == "Mining Weekly"

    def test_from_api_handles_missing_fields(self):
        article = Article.from_api({})
        assert article.title is None
        assert article.url is None
        assert article.source is None

    def test_from_api_handles_missing_source_name(self):
        article = Article.from_api({"source": {}})
        assert article.source is None


class TestMiningNewsClient:
    """MiningNewsClient"""

    def test_init_reads_env_var(self, mock_newsapi_key):
        client = MiningNewsClient()
        assert client.api_key == "test-key-12345"

    def test_init_accepts_explicit_key(self):
        client = MiningNewsClient(api_key="explicit-key")
        assert client.api_key == "explicit-key"

    def test_init_warns_on_missing_key(self, caplog):
        with pytest.MonkeyPatch.context() as mp:
            mp.delenv("NEWS_API_KEY", raising=False)
            client = MiningNewsClient()
            assert client.api_key == ""

    def test_search_raises_without_key(self):
        with pytest.MonkeyPatch.context() as mp:
            mp.delenv("NEWS_API_KEY", raising=False)
            client = MiningNewsClient(api_key="")
            with pytest.raises(ValueError, match="NEWS_API_KEY"):
                client.search("test")

    def test_search_returns_search_result(
        self, mock_newsapi_key, sample_newsapi_response
    ):
        import newsapi

        # Mock NewsApiClient.get_everything
        original = newsapi.NewsApiClient.get_everything
        newsapi.NewsApiClient.get_everything = lambda self, **kw: sample_newsapi_response
        try:
            client = MiningNewsClient()
            result = client.search("lithium", days=7)

            assert isinstance(result, SearchResult)
            assert len(result.articles) == 1
            assert result.articles[0].title == "Lithium Prices Surge Amid EV Demand"
            assert result.articles[0].source == "Mining Weekly"
            assert result.query == "lithium"
        finally:
            newsapi.NewsApiClient.get_everything = original

    def test_search_raises_on_api_error(self, mock_newsapi_key):
        client = MiningNewsClient()

        import newsapi
        original = newsapi.NewsApiClient.get_everything
        newsapi.NewsApiClient.get_everything = lambda self, **kw: {
            "status": "error",
            "message": "API key invalid",
        }
        try:
            with pytest.raises(RuntimeError, match="API key invalid"):
                client.search("test")
        finally:
            newsapi.NewsApiClient.get_everything = original
