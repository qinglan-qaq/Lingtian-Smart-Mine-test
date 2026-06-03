"""
mining-news-mcp 包初始化

暴露核心 API 便于外部引用:
    from mining_news_mcp import MiningNewsClient, search_news
"""

from .news_api import Article, MiningNewsClient, SearchResult
from .tools import fetch_article_content, search_news

__all__ = [
    "MiningNewsClient",
    "SearchResult",
    "Article",
    "search_news",
    "fetch_article_content",
]
