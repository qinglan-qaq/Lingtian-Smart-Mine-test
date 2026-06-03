"""
mining-news-mcp 业务逻辑层

纯函数，不依赖 FastMCP。被 server.py 的 @mcp.tool() 装饰器调用。
"""

import logging
from typing import Any

import httpx
from bs4 import BeautifulSoup

from .news_api import MiningNewsClient

logger = logging.getLogger(__name__)

# ── 常量 ─────────────────────────────────────────────────
ARTICLE_MAX_LENGTH = 5000   # fetch_article 最大返回字符数
REQUEST_TIMEOUT = 15.0       # HTTP 请求超时（秒）
USER_AGENT = "MiningDailyBot/1.0 (compatible; mining-news-mcp)"


# ── search ───────────────────────────────────────────────

def search_news(query: str, days: int = 7) -> list[dict[str, Any]]:
    """
    搜索矿业新闻。

    对 NewsAPI 的封装，返回 Agent 友好的 dict 列表。

    Args:
        query: 搜索关键词（中英文均可）
        days: 回溯天数，默认 7

    Returns:
        [{title, url, description, published_at, source}, ...]
        出错时返回 [{"error": "..."}]
    """
    logger.info("search_news: query='%s', days=%d", query, days)

    try:
        client = MiningNewsClient()
        result = client.search(query, days=days)
    except ValueError as exc:
        logger.warning("search_news 配置错误: %s", exc)
        return [{"error": f"Configuration error: {exc}"}]
    except RuntimeError as exc:
        logger.error("search_news API 错误: %s", exc)
        return [{"error": f"NewsAPI error: {exc}"}]
    except Exception as exc:
        logger.exception("search_news 未知错误: %s", exc)
        return [{"error": f"Unexpected error: {exc}"}]

    return [
        {
            "title": a.title,
            "url": a.url,
            "description": a.description,
            "published_at": a.published_at,
            "source": a.source,
        }
        for a in result.articles
    ]


# ── fetch_article ────────────────────────────────────────

async def fetch_article_content(url: str) -> str:
    """
    抓取并清洗文章正文。

    使用 httpx + BeautifulSoup 提取 <p> 标签文本。

    Args:
        url: 文章 URL

    Returns:
        清洗后的纯文本（最多 {ARTICLE_MAX_LENGTH} 字符）。
        失败时返回以 "Error:" 或 "Failed:" 开头的字符串。
    """
    logger.info("fetch_article: url='%s'", url)

    if not url or not url.startswith(("http://", "https://")):
        return f"Error: invalid URL: {url!r}"

    headers = {"User-Agent": USER_AGENT}

    try:
        async with httpx.AsyncClient(timeout=REQUEST_TIMEOUT) as client:
            resp = await client.get(url, headers=headers, follow_redirects=True)
            resp.raise_for_status()

        soup = BeautifulSoup(resp.text, "lxml")
        # 移除 script / style 标签
        for tag in soup(["script", "style", "nav", "footer", "header"]):
            tag.decompose()

        paragraphs = soup.find_all("p")
        text = "\n".join(p.get_text(strip=True) for p in paragraphs if p.get_text(strip=True))

        if not text:
            logger.warning("fetch_article: 未提取到文本 content from %s", url)
            return f"Warning: No text content extracted from {url}"

        truncated = text[:ARTICLE_MAX_LENGTH]
        if len(text) > ARTICLE_MAX_LENGTH:
            logger.debug("fetch_article: 截断 %d → %d chars", len(text), ARTICLE_MAX_LENGTH)

        return truncated

    except httpx.HTTPStatusError as exc:
        logger.error("fetch_article HTTP %d: %s", exc.response.status_code, url)
        return f"Failed to fetch article: HTTP {exc.response.status_code}"
    except httpx.TimeoutException:
        logger.error("fetch_article 超时: %s", url)
        return f"Failed to fetch article: timeout after {REQUEST_TIMEOUT}s"
    except Exception as exc:
        logger.exception("fetch_article 未知错误: %s", exc)
        return f"Failed to fetch article: {exc}"
