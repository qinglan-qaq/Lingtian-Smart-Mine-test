"""
mining-news-mcp — FastMCP Server 入口

基于 MCP (Model Context Protocol) 协议，通过 stdio transport 暴露工具:
  - search:  搜索矿业新闻 (NewsAPI)
  - fetch_article: 抓取文章全文 (httpx + BeautifulSoup)

启动方式:
    python -m mining_news_mcp              # 通过 __main__.py
    python -m mining_news_mcp.server       # 直接运行本文件
"""

import logging
import os
import sys
from typing import Any

from dotenv import load_dotenv
from mcp.server.fastmcp import FastMCP

from .tools import fetch_article_content, search_news

# 加载 .env（从项目根目录）
load_dotenv()

# ── 日志配置 ────────────────────────────────────────────────
logging.basicConfig(
    level=getattr(logging, os.getenv("LOG_LEVEL", "INFO")),
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    stream=sys.stderr,  # stderr 不干扰 stdio transport
)
logger = logging.getLogger("mining-news-mcp")

# ── FastMCP 实例 ────────────────────────────────────────────
mcp = FastMCP("mining-news-mcp")


# ── Tool: search ────────────────────────────────────────────

@mcp.tool()
async def search(query: str, days: int = 7) -> list[dict[str, Any]]:
    """
    搜索最近 N 天的矿业新闻。

    返回新闻标题、URL、摘要、来源和发布时间。
    适用于获取与特定矿种、矿区或公司相关的近期新闻。

    Args:
        query: 搜索关键词（中英文均可），如 'Pilbara lithium'、'铜矿 价格'
        days: 回溯天数，默认 7
    """
    logger.info("[tool:search] query='%s', days=%d", query, days)

    # 参数校验
    if not query or not query.strip():
        return [{"error": "query 不能为空"}]
    if days < 1 or days > 30:
        return [{"error": f"days 必须在 1-30 之间，收到: {days}"}]

    return search_news(query.strip(), days)


# ── Tool: fetch_article ─────────────────────────────────────

@mcp.tool()
async def fetch_article(url: str) -> str:
    """
    获取指定 URL 的文章全文（清洗后的纯文本）。

    抓取网页并提取正文，自动去除 script/style/nav/footer/header。
    最多返回 5000 字符。

    Args:
        url: 新闻文章的完整 URL
    """
    logger.info("[tool:fetch_article] url='%s'", url)
    return await fetch_article_content(url)


# ── 入口 ────────────────────────────────────────────────────

def main():
    """stdio transport 入口"""
    logger.info("mining-news-mcp 启动中... (NEWS_API_KEY=%s)",
                "***" if os.getenv("NEWS_API_KEY") else "NOT SET")
    mcp.run(transport="stdio")


if __name__ == "__main__":
    main()
