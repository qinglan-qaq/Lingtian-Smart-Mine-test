"""
MCP Client — 连接并管理与 3 个 MCP Server 的通信

在 Executor 节点中被调用，每个 tool_call 路由到对应的 MCP Server。
"""

import json
import logging
from dataclasses import dataclass, field

logger = logging.getLogger(__name__)


@dataclass
class MCPServerConfig:
    """MCP Server 连接配置"""
    name: str
    command: str = "python"
    args: list[str] = field(default_factory=list)
    env: dict[str, str] = field(default_factory=dict)


class MCPClientManager:
    """
    管理多个 MCP Server 的连接与工具调用。

    用法:
        manager = MCPClientManager([
            MCPServerConfig(name="mining-news", args=["-m", "mining_news_mcp.server"]),
            MCPServerConfig(name="mineral-pdf", args=["-m", "mineral_pdf_mcp.server"]),
            MCPServerConfig(name="lme-price",  args=["-m", "lme_price_mcp.server"]),
        ])
        await manager.connect_all()
        result = await manager.call_tool("search_mining_news", {"query": "lithium"})
        await manager.disconnect_all()
    """

    # 工具名 → MCP Server 名 的路由表
    TOOL_ROUTING: dict[str, str] = {
        "search_mining_news": "mining-news",
        "fetch_article":      "mining-news",
        "extract_resources":  "mineral-pdf",
        "get_price":          "lme-price",
        "get_price_trend":    "lme-price",
    }

    def __init__(self, servers: list[MCPServerConfig]):
        self.servers: dict[str, MCPServerConfig] = {s.name: s for s in servers}
        self._sessions: dict[str, object] = {}  # name → MCP session
        self._connected = False

    # ── 连接管理 ─────────────────────────────────────────

    async def connect_all(self) -> None:
        """
        连接所有 MCP Server 并发现工具。

        使用 stdio transport 启动子进程。每个 server 以 python -m <module> 方式运行。
        """
        if self._connected:
            return

        for name, server in self.servers.items():
            try:
                # TODO: 替换为真实 mcp SDK 连接
                # from mcp.client.stdio import stdio_client
                # transport = await stdio_client(server.command, server.args, env=server.env)
                # session = await ClientSession(transport)
                # await session.initialize()
                # self._sessions[name] = session
                logger.info(f"MCP [{name}]: configured (command={server.command}, args={server.args})")
            except Exception as exc:
                logger.error(f"MCP [{name}]: 连接失败 — {exc}")

        self._connected = True
        logger.info(f"MCP Client: {len(self.servers)} servers configured")

    async def disconnect_all(self) -> None:
        """断开所有 MCP 连接"""
        for name, session in self._sessions.items():
            try:
                # TODO: await session.close()
                ...
            except Exception:
                pass
        self._sessions.clear()
        self._connected = False
        logger.info("MCP Client: disconnected")

    # ── 工具调用 ─────────────────────────────────────────

    async def call_tool(self, tool_name: str, arguments: dict) -> str:
        """
        调用指定 MCP 工具，自动路由到正确的 Server。

        Args:
            tool_name: 工具名 (如 search_mining_news)
            arguments: 工具参数

        Returns:
            工具执行结果（字符串）

        Raises:
            ValueError: 未知工具名
            RuntimeError: MCP Server 未连接
        """
        server_name = self.TOOL_ROUTING.get(tool_name)
        if server_name is None:
            raise ValueError(f"未知工具: {tool_name}，路由表未注册")

        session = self._sessions.get(server_name)
        if session is None:
            # 兜底：返回 mock 数据用于开发阶段
            logger.warning(
                f"MCP [{server_name}] 未连接，{tool_name}({arguments}) 返回 mock 数据"
            )
            return self._mock_result(tool_name, arguments)

        # TODO: 真实 MCP 调用
        # result = await session.call_tool(tool_name, arguments)
        # return result.content[0].text
        return self._mock_result(tool_name, arguments)

    # ── Mock 数据（开发阶段，接入真实 API 后移除）─────────

    def _mock_result(self, tool_name: str, arguments: dict) -> str:
        """生成 mock 返回数据，方便开发调试"""
        if tool_name == "search_mining_news":
            query = arguments.get("query", "")
            return json.dumps({
                "articles": [
                    {
                        "title": f"[Mock] {query} 矿业最新动态",
                        "source": "Mining Weekly",
                        "url": "https://www.miningweekly.com/mock",
                        "summary": f"关于 {query} 的 mock 新闻摘要。（接入 NewsAPI 后替换为真实数据）",
                        "published_at": "2026-06-03",
                    }
                ],
                "total": 1,
            }, ensure_ascii=False)

        if tool_name == "fetch_article":
            return json.dumps({
                "title": "[Mock] 文章标题",
                "content": "（Mock 文章正文 — 接入后替换为真实内容）",
                "source": arguments.get("url", ""),
                "published_at": "2026-06-03",
            }, ensure_ascii=False)

        if tool_name == "extract_resources":
            return json.dumps({
                "project_name": "[Mock] Sample Mining Project",
                "mineral": "lithium",
                "indicated": {"tonnage": 10.5, "grade": 1.2, "unit": "Mt @ %Li2O"},
                "inferred":  {"tonnage": 5.2,  "grade": 0.9, "unit": "Mt @ %Li2O"},
                "report_date": "2025-01-15",
                "source_url": arguments.get("pdf_url", ""),
            }, ensure_ascii=False)

        if tool_name == "get_price":
            commodity = arguments.get("commodity", "")
            return json.dumps({
                "commodity": commodity,
                "price": 12500,
                "currency": "USD",
                "unit": "per metric ton",
                "date": arguments.get("date", "2026-06-03"),
            }, ensure_ascii=False)

        if tool_name == "get_price_trend":
            commodity = arguments.get("commodity", "")
            days = arguments.get("days", 30)
            return json.dumps({
                "commodity": commodity,
                "trend": [{"date": f"2026-05-{d:02d}", "price": 12000 + d * 20} for d in range(1, min(days, 31))],
                "change_pct": 5.2,
            }, ensure_ascii=False)

        return json.dumps({"error": f"未知工具 {tool_name}"})
