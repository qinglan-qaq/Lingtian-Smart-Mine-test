"""
NewsAPI 封装
"""

import os

import httpx

NEWSAPI_BASE_URL = "https://newsapi.org/v2"


class NewsAPIClient:
    """NewsAPI HTTP 客户端"""

    def __init__(self, api_key: str | None = None):
        self.api_key = api_key or os.getenv("NEWSAPI_KEY", "")
        self.client = httpx.AsyncClient(
            base_url=NEWSAPI_BASE_URL,
            headers={"X-Api-Key": self.api_key},
        )

    async def search(self, query: str, days: int = 7) -> dict:
        """搜索新闻"""
        # TODO: 实现 NewsAPI everything endpoint 调用
        ...

    async def close(self):
        await self.client.aclose()
