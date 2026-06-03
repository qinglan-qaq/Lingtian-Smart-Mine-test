"""
Agent 工具 Schema 定义

工具名与 MCP Server 的 @mcp.tool() 保持严格一致：
  - search           → mining-news-mcp 的 search()
  - fetch_article    → mining-news-mcp 的 fetch_article()
  - extract_resources → mineral-pdf-mcp 的 extract_resources()
  - get_price         → lme-price-mcp 的 get_price()
  - get_trend         → lme-price-mcp 的 get_trend()

在 Think 节点中通过 prompt 告知 LLM 可用工具。
实际执行由 Executor 节点通过 MCPClientManager 完成。
"""

TOOL_DEFINITIONS = [
    {
        "name": "search",
        "description": (
            "搜索矿业相关新闻。"
            "适用于获取与特定矿种、矿区或公司相关的近期新闻。"
            "返回新闻标题、URL、摘要、来源和发布时间。"
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "query": {
                    "type": "string",
                    "description": "搜索关键词（中英文均可），如 'Pilbara lithium'、'copper price'",
                },
                "days": {
                    "type": "integer",
                    "description": "搜索最近 N 天的新闻，默认 7（范围 1-30）",
                },
            },
            "required": ["query"],
        },
    },
    {
        "name": "fetch_article",
        "description": (
            "获取新闻文章全文内容（清洗后的纯文本）。"
            "当需要了解某篇新闻的详细内容时调用。"
            "最多返回 5000 字符。"
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "url": {
                    "type": "string",
                    "description": "新闻文章的完整 URL",
                },
            },
            "required": ["url"],
        },
    },
    {
        "name": "extract_resources",
        "description": (
            "从 PDF 报告中提取 NI 43-101 标准的矿产资源和储量数据。"
            "提取 Indicated（控制资源量）和 Inferred（推断资源量）的吨位与品位。"
            "适用于已有 NI 43-101 技术报告的矿区分析。"
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "pdf_url": {
                    "type": "string",
                    "description": "NI 43-101 技术报告的 PDF URL",
                },
            },
            "required": ["pdf_url"],
        },
    },
    {
        "name": "get_price",
        "description": (
            "获取指定矿产的当前市场价格。"
            "支持的矿产: lithium(锂), copper(铜), gold(金), silver(银), "
            "iron-ore(铁矿石), nickel(镍), cobalt(钴), rare-earth(稀土), uranium(铀)。"
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "commodity": {
                    "type": "string",
                    "description": "矿产名称（英文小写），如 lithium, copper, gold",
                },
                "date": {
                    "type": "string",
                    "description": "价格日期，格式 YYYY-MM-DD。不填则返回最新价格",
                },
            },
            "required": ["commodity"],
        },
    },
    {
        "name": "get_trend",
        "description": (
            "获取指定矿产的近期价格趋势数据。"
            "返回日级价格序列和涨跌幅，用于走势分析。"
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "commodity": {
                    "type": "string",
                    "description": "矿产名称（英文小写）",
                },
                "days": {
                    "type": "integer",
                    "description": "回溯天数，默认 30",
                },
            },
            "required": ["commodity"],
        },
    },
]
