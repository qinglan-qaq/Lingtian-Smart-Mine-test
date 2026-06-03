"""
lme-price-mcp — MCP Server 入口
提供 get_price(commodity, date) 和 get_trend(commodity, days) 两个工具
"""

import asyncio
import logging

from dotenv import load_dotenv

from .tools import get_price, get_trend

load_dotenv()

logger = logging.getLogger(__name__)


async def serve():
    """启动 MCP Server (stdio 模式)"""
    # TODO: 使用 mcp SDK 注册工具并启动
    logger.info("lme-price-mcp server started")


def main():
    asyncio.run(serve())


if __name__ == "__main__":
    main()
