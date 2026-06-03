"""
Agent 工具定义 — 封装 MCP Client 调用
"""

import logging

logger = logging.getLogger(__name__)


# MCP 工具调用将通过 agent/graph.py 中的 ToolNode 动态绑定
# 此处定义工具的 schema 描述

TOOL_DEFINITIONS = [
    {
        "name": "search_mining_news",
        "description": "搜索矿业相关新闻",
        "parameters": {
            "type": "object",
            "properties": {
                "query": {"type": "string", "description": "搜索关键词"},
                "days": {"type": "integer", "description": "搜索最近 N 天", "default": 7},
            },
            "required": ["query"],
        },
    },
    {
        "name": "fetch_article",
        "description": "获取新闻文章全文",
        "parameters": {
            "type": "object",
            "properties": {
                "url": {"type": "string", "description": "文章 URL"},
            },
            "required": ["url"],
        },
    },
    {
        "name": "extract_resources",
        "description": "从 PDF 提取 NI 43-101 标准的 Indicated/Inferred 储量数据",
        "parameters": {
            "type": "object",
            "properties": {
                "pdf_url": {"type": "string", "description": "PDF 报告的 URL"},
            },
            "required": ["pdf_url"],
        },
    },
    {
        "name": "get_price",
        "description": "获取指定矿产的当前价格",
        "parameters": {
            "type": "object",
            "properties": {
                "commodity": {"type": "string", "description": "矿产名称，如 lithium, copper, gold"},
                "date": {"type": "string", "description": "日期 YYYY-MM-DD，默认今天"},
            },
            "required": ["commodity"],
        },
    },
    {
        "name": "get_price_trend",
        "description": "获取指定矿产的价格趋势",
        "parameters": {
            "type": "object",
            "properties": {
                "commodity": {"type": "string", "description": "矿产名称"},
                "days": {"type": "integer", "description": "趋势天数", "default": 30},
            },
            "required": ["commodity"],
        },
    },
]
