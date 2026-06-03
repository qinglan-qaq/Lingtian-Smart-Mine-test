"""
矿权日报 Agent — 主入口
基于 LangGraph ReAct 模式，编排 3 个 MCP Server 生成日报简报
"""

import argparse
import asyncio
import logging

from dotenv import load_dotenv

from .agent.graph import create_agent_graph
from .utils.config import get_config

load_dotenv()

logger = logging.getLogger(__name__)


async def run(prompt: str) -> str:
    """运行 Agent，返回 Markdown 简报"""
    config = get_config()
    graph = create_agent_graph()

    result = await graph.ainvoke(
        {"messages": [{"role": "user", "content": prompt}]},
        config={"configurable": {"mcp_servers": config.mcp_servers}},
    )

    return result["messages"][-1].content


def main():
    parser = argparse.ArgumentParser(description="矿权日报 Agent")
    parser.add_argument(
        "--prompt", "-p",
        type=str,
        default="给我生成一份关于 Pilbara 锂矿的今日简报",
        help="输入提示词",
    )
    parser.add_argument(
        "--log-level",
        default="INFO",
        choices=["DEBUG", "INFO", "WARNING", "ERROR"],
    )
    args = parser.parse_args()

    logging.basicConfig(level=args.log_level)

    report = asyncio.run(run(args.prompt))
    print(report)


if __name__ == "__main__":
    main()
