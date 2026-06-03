"""
mining-news-mcp — MCP Server 入口
提供 search(query, days) 和 fetch_article(url) 两个工具
"""

import asyncio
import logging
import os

from dotenv import load_dotenv

from .tools import fetch_article, search_news

load_dotenv()

logger = logging.getLogger(__name__)


async def serve():
    """启动 MCP Server (stdio 模式)"""
    # TODO: 使用 mcp SDK 注册工具并启动
    # from mcp.server import Server
    # server = Server("mining-news-mcp")
    # server.tool("search_news")(search_news)
    # server.tool("fetch_article")(fetch_article)
    # await server.run()
    logger.info("mining-news-mcp server started")


def main():
    asyncio.run(serve())


if __name__ == "__main__":
    main()
