"""
配置管理 — 从 .env 读取所有配置
"""

import os
from dataclasses import dataclass, field


@dataclass
class Config:
    llm_api_key: str = ""
    llm_model: str = "gpt-4o"
    llm_base_url: str = "https://api.openai.com/v1"
    log_level: str = "INFO"
    mcp_servers: list[dict] = field(default_factory=list)


def get_config() -> Config:
    return Config(
        llm_api_key=os.getenv("LLM_API_KEY", ""),
        llm_model=os.getenv("LLM_MODEL", "gpt-4o"),
        llm_base_url=os.getenv("LLM_BASE_URL", "https://api.openai.com/v1"),
        log_level=os.getenv("LOG_LEVEL", "INFO"),
        mcp_servers=[
            {
                "name": "mining-news",
                "command": "python",
                "args": ["-m", "mining_news_mcp.server"],
            },
            {
                "name": "mineral-pdf",
                "command": "python",
                "args": ["-m", "mineral_pdf_mcp.server"],
            },
            {
                "name": "lme-price",
                "command": "python",
                "args": ["-m", "lme_price_mcp.server"],
            },
        ],
    )
