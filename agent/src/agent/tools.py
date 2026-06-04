"""
Agent 工具定义 — 静态 schema，供 prompt 生成和 MCP 路由使用。

工具名与各 MCP Server 的 @mcp.tool() 名称严格一致。
实际执行由 Executor 节点通过 MCPClientManager 完成。
"""

from typing import Any

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
            "required": ["commodity", "date"],
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


# ── 工具 → MCP Server 路由 ───────────────────────────────

TOOL_ROUTING: dict[str, str] = {}
for _td in TOOL_DEFINITIONS:
    _name = _td["name"]
    if _name in ("search", "fetch_article"):
        TOOL_ROUTING[_name] = "mining-news"
    elif _name == "extract_resources":
        TOOL_ROUTING[_name] = "mineral-pdf"
    else:
        TOOL_ROUTING[_name] = "lme-price"
