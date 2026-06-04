"""
Agent 工具定义 — 静态 schema + MCP 动态加载

- TOOL_DEFINITIONS: 静态 schema，供 prompt 生成
- load_mcp_tools(): 通过 langchain-mcp 连接远程 MCP Server
- get_tool_map(): 构建 {tool_name: callable} 映射供 Executor 使用
"""

import logging
from typing import Any

logger = logging.getLogger(__name__)

# ── 静态工具 Schema ──────────────────────────────────────

TOOL_DEFINITIONS: list[dict[str, Any]] = [
    {
        "name": "search",
        "description": "搜索矿业相关新闻，返回标题、URL、摘要、来源和发布时间。",
        "parameters": {
            "type": "object",
            "properties": {
                "query": {"type": "string", "description": "搜索关键词（中英文均可）"},
                "days": {"type": "integer", "description": "搜索最近 N 天，默认 7"},
            },
            "required": ["query"],
        },
    },
    {
        "name": "fetch_article",
        "description": "获取新闻文章全文（清洗后的纯文本，最多 5000 字符）。",
        "parameters": {
            "type": "object",
            "properties": {
                "url": {"type": "string", "description": "新闻文章完整 URL"},
            },
            "required": ["url"],
        },
    },
    {
        "name": "extract_resources",
        "description": "从 PDF 提取 NI 43-101 标准储量数据：Indicated/Inferred/Measured/Proven。",
        "parameters": {
            "type": "object",
            "properties": {
                "pdf_url": {"type": "string", "description": "NI 43-101 技术报告 PDF URL"},
            },
            "required": ["pdf_url"],
        },
    },
    {
        "name": "get_price",
        "description": "获取矿产当前价格（美元/吨）。支持 lithium, copper, gold, silver, iron-ore, nickel, cobalt, rare-earth, uranium。",
        "parameters": {
            "type": "object",
            "properties": {
                "commodity": {"type": "string", "description": "矿产名称（英文小写）"},
                "date": {"type": "string", "description": "日期 YYYY-MM-DD，不填则最新"},
            },
            "required": ["commodity"],
        },
    },
    {
        "name": "get_trend",
        "description": "获取矿产近期价格趋势，返回日级序列和涨跌幅。",
        "parameters": {
            "type": "object",
            "properties": {
                "commodity": {"type": "string", "description": "矿产名称"},
                "days": {"type": "integer", "description": "回溯天数，默认 30"},
            },
            "required": ["commodity"],
        },
    },
]


# ── 工具名称 → (MCP Server, Tool 元数据) 路由 ─────────────

TOOL_ROUTING: dict[str, tuple[str, dict]] = {}
for _td in TOOL_DEFINITIONS:
    _name = _td["name"]
    if _name in ("search", "fetch_article"):
        TOOL_ROUTING[_name] = ("mining-news", _td)
    elif _name == "extract_resources":
        TOOL_ROUTING[_name] = ("mineral-pdf", _td)
    else:
        TOOL_ROUTING[_name] = ("lme-price", _td)


# ── langchain-mcp 工具加载 ───────────────────────────────

async def load_mcp_tools(
    server_configs: list[dict[str, Any]],
) -> dict[str, Any]:
    """
    通过 langchain-mcp 连接远程 MCP Server 并加载工具。

    Args:
        server_configs: [{"name": "...", "command": "...", "args": [...]}, ...]

    Returns:
        {tool_name: LangChain BaseTool}
    """
    try:
        from langchain_mcp import MultiServerMCPClient
    except ImportError:
        logger.debug("langchain-mcp 未安装，跳过 MCP 工具加载")
        return {}

    mcp_config: dict[str, dict] = {}
    for srv in server_configs:
        mcp_config[srv["name"]] = {
            "transport": "stdio",
            "command": srv.get("command", "python"),
            "args": srv.get("args", []),
        }

    try:
        client = MultiServerMCPClient(mcp_config)
        tools = await client.get_tools()
        tool_map = {t.name: t for t in tools}
        logger.info("langchain-mcp 加载 %d 个工具: %s", len(tool_map), list(tool_map.keys()))
        return tool_map
    except Exception as exc:
        logger.warning("langchain-mcp 连接失败: %s", exc)
        return {}


# ── tool_map 构建 ────────────────────────────────────────

async def get_tool_map(
    config: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """
    构建 {tool_name: callable} 映射。

    优先从 langchain-mcp 加载真实工具，回退到 MCPClientManager mock。

    Args:
        config: 运行时 config（含 configurable.mcp_manager 和 configurable.mcp_servers）

    Returns:
        {"search": BaseTool, "fetch_article": BaseTool, ...}
    """
    cfg = (config or {}).get("configurable", {})
    mcp_manager = cfg.get("mcp_manager")

    # 路径1: langchain-mcp
    if cfg.get("mcp_servers"):
        lc_tools = await load_mcp_tools(cfg["mcp_servers"])
        if lc_tools:
            return lc_tools

    # 路径2: MCPClientManager (fallback)
    if mcp_manager is not None:
        from functools import partial

        tool_map = {}
        for name, (server, _td) in TOOL_ROUTING.items():
            async def _call(name=name, server=server):
                return await mcp_manager.call_tool(name, {})

            tool_map[name] = partial(mcp_manager.call_tool, tool_name=name)
        return tool_map

    logger.warning("无可用的 MCP 工具加载路径，tool_map 为空")
    return {}
