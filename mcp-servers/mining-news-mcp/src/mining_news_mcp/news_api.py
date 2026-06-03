"""
NewsAPI HTTP 客户端 — 封装 newsapi.org /v2/everything 端点。

使用 newsapi-python 官方 SDK，提供同步/异步搜索能力。
"""

import logging
import os
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import Any

from newsapi import NewsApiClient

logger = logging.getLogger(__name__)

# ── 常量 ─────────────────────────────────────────────────
DEFAULT_PAGE_SIZE = 10
MAX_PAGE_SIZE = 100


# ── 数据结构 ─────────────────────────────────────────────


@dataclass
class Article:
    """标准化新闻条目"""

    title: str | None
    url: str | None
    description: str | None
    published_at: str | None
    source: str | None

    @classmethod
    def from_api(cls, raw: dict[str, Any]) -> "Article":
        return cls(
            title=raw.get("title"),
            url=raw.get("url"),
            description=raw.get("description"),
            published_at=raw.get("publishedAt"),
            source=(raw.get("source") or {}).get("name"),
        )


@dataclass
class SearchResult:
    """搜索结果"""

    articles: list[Article]
    total: int
    query: str
    page: int
    page_size: int


# ── 客户端 ───────────────────────────────────────────────


class MiningNewsClient:
    """
    矿业新闻搜索客户端。

    封装 NewsAPI，负责:
        - API 认证
        - 日期范围计算
        - 结果标准化
        - 错误处理

    用法:
        client = MiningNewsClient()           # 从 NEWS_API_KEY 环境变量读取
        # 或
        client = MiningNewsClient(api_key="...")

        result = client.search("Pilbara lithium", days=7)
        for article in result.articles:
            print(article.title)
    """

    def __init__(self, api_key: str | None = None):
        """
        Args:
            api_key: NewsAPI key。不传则从环境变量 NEWS_API_KEY 读取。
        """
        self.api_key = api_key or os.getenv("NEWS_API_KEY", "")
        if not self.api_key:
            logger.warning(
                "NEWS_API_KEY 未设置，NewsAPI 请求将失败。"
                "请在 .env 中配置 NEWS_API_KEY=your_key"
            )
        self._client = NewsApiClient(api_key=self.api_key)

    # ── 公开方法 ──────────────────────────────────────

    def search(
        self,
        query: str,
        days: int = 7,
        language: str = "en",
        page: int = 1,
        page_size: int = DEFAULT_PAGE_SIZE,
        sort_by: str = "relevancy",
    ) -> SearchResult:
        """
        搜索新闻。

        Args:
            query: 搜索关键词（支持 AND / OR / 短语）
            days: 回溯天数
            language: 语言代码
            page: 页码
            page_size: 每页条数 (max 100)
            sort_by: 排序方式 — relevancy / popularity / publishedAt

        Returns:
            SearchResult 包含标准化文章列表

        Raises:
            ValueError: API key 未配置
            RuntimeError: API 请求失败
        """
        if not self.api_key:
            raise ValueError("NEWS_API_KEY 未配置，无法调用 NewsAPI")

        to_date = datetime.now()
        from_date = to_date - timedelta(days=days)

        try:
            response = self._client.get_everything(
                q=query,
                from_param=from_date.strftime("%Y-%m-%d"),
                to=to_date.strftime("%Y-%m-%d"),
                language=language,
                sort_by=sort_by,
                page=page,
                page_size=min(page_size, MAX_PAGE_SIZE),
            )
        except Exception as exc:
            logger.error(f"NewsAPI 请求失败: {exc}")
            raise RuntimeError(f"NewsAPI request failed: {exc}") from exc

        status = response.get("status", "")
        if status != "ok":
            msg = response.get("message", "unknown error")
            logger.error(f"NewsAPI 返回错误状态: {status} — {msg}")
            raise RuntimeError(f"NewsAPI error: {msg}")

        articles = [Article.from_api(a) for a in response.get("articles", [])]

        logger.info(
            "NewsAPI search: query='%s', days=%d, found=%d",
            query,
            days,
            len(articles),
        )

        return SearchResult(
            articles=articles,
            total=response.get("totalResults", len(articles)),
            query=query,
            page=page,
            page_size=page_size,
        )
