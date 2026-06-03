"""
mineral-pdf-mcp — MCP Server 入口
提供 extract_resources(pdf_url) 工具 — NI 43-101 Indicated/Inferred 储量提取
"""

import asyncio
import logging

from dotenv import load_dotenv

from .tools import extract_resources

load_dotenv()

logger = logging.getLogger(__name__)


async def serve():
    """启动 MCP Server (stdio 模式)"""
    # TODO: 使用 mcp SDK 注册工具并启动
    logger.info("mineral-pdf-mcp server started")


def main():
    asyncio.run(serve())


if __name__ == "__main__":
    main()
