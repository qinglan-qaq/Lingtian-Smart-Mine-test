"""
lme-price-mcp 工具实现 — 矿产价格数据
"""

import logging

logger = logging.getLogger(__name__)


async def get_price(commodity: str, date: str | None = None) -> dict:
    """
    获取指定矿产的价格
    Args:
        commodity: 矿产名称 (lithium, copper, gold, iron-ore, nickel, cobalt, rare-earth 等)
        date: 日期 YYYY-MM-DD，默认最新
    Returns:
        {"commodity": str, "price": float, "currency": str, "unit": str, "date": str}
    """
    # TODO: 调用价格 API
    logger.info(f"get_price: commodity={commodity}, date={date}")
    return {
        "commodity": commodity,
        "price": 0.0,
        "currency": "USD",
        "unit": "",
        "date": date or "",
    }


async def get_trend(commodity: str, days: int = 30) -> dict:
    """
    获取矿产价格趋势
    Args:
        commodity: 矿产名称
        days: 趋势天数
    Returns:
        {"commodity": str, "trend": [{"date": str, "price": float}], "change_pct": float}
    """
    # TODO: 调用价格趋势 API
    logger.info(f"get_trend: commodity={commodity}, days={days}")
    return {
        "commodity": commodity,
        "trend": [],
        "change_pct": 0.0,
    }
