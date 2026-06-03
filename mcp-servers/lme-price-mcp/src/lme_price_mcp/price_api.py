"""
价格 API 封装 — LME / 其他矿产价格数据源
"""

import os

import httpx


class PriceAPIClient:
    """矿产价格 HTTP 客户端"""

    def __init__(self, api_key: str | None = None, base_url: str | None = None):
        self.api_key = api_key or os.getenv("LME_API_KEY", "")
        self.base_url = base_url or os.getenv("LME_API_BASE_URL", "")
        self.client = httpx.AsyncClient(
            base_url=self.base_url,
            headers={"Authorization": f"Bearer {self.api_key}"},
        )

    # 支持的矿产列表
    COMMODITIES = [
        "lithium",
        "copper",
        "gold",
        "silver",
        "iron-ore",
        "nickel",
        "cobalt",
        "rare-earth",
        "uranium",
    ]

    async def get_price(self, commodity: str, date: str | None = None) -> dict:
        """获取矿产价格"""
        # TODO: 实现价格查询 endpoint 调用
        ...

    async def get_trend(self, commodity: str, days: int = 30) -> dict:
        """获取价格趋势"""
        # TODO: 实现趋势查询 endpoint 调用
        ...

    async def close(self):
        await self.client.aclose()
