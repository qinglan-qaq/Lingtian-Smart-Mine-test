"""
lme-price-mcp — FastMCP Server 入口

通过 stdio transport 暴露:
  - get_price:  矿产价格（yfinance LIT ETF / 模拟回退）
  - get_trend:  价格趋势序列（yfinance / 模拟回退）
"""

import logging
import os
import sys
from datetime import datetime, timedelta

from dotenv import load_dotenv
from mcp.server.fastmcp import FastMCP

from .price_simulator import PriceSimulator

load_dotenv()

logging.basicConfig(
    level=getattr(logging, os.getenv("LOG_LEVEL", "INFO")),
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    stream=sys.stderr,
)
logger = logging.getLogger("lme-price-mcp")

# ── yfinance 可选导入 ─────────────────────────────────────
try:
    import yfinance as yf

    _use_yf = True
except ImportError:
    _use_yf = False
    logger.info("yfinance 未安装，将仅使用模拟价格数据")

# ── FastMCP 实例 ──────────────────────────────────────────
mcp = FastMCP("lme-price-mcp")
_sim = PriceSimulator()

# ── 常量 ──────────────────────────────────────────────────
ETF_TICKER = "LIT"  # Global X Lithium & Battery Tech ETF


# ── helpers ───────────────────────────────────────────────

def _try_yf_price(date_str: str) -> float | None:
    """尝试从 yfinance 获取 LIT ETF 收盘价，失败返回 None"""
    if not _use_yf:
        return None
    try:
        date_dt = datetime.strptime(date_str, "%Y-%m-%d")
        end_dt = date_dt + timedelta(days=1)
        ticker = yf.Ticker(ETF_TICKER)
        hist = ticker.history(start=date_str, end=end_dt.strftime("%Y-%m-%d"), progress=False)
        if hist.empty:
            return None
        close = float(hist["Close"].iloc[-1])
        logger.info("yfinance LIT close on %s: %.2f", date_str, close)
        return close
    except Exception as exc:
        logger.debug("yfinance get_price 失败: %s", exc)
        return None


def _try_yf_trend(days: int) -> list[dict] | None:
    """尝试从 yfinance 获取 LIT ETF 历史价格序列，失败返回 None"""
    if not _use_yf:
        return None
    try:
        end = datetime.now()
        start = end - timedelta(days=days + 1)
        ticker = yf.Ticker(ETF_TICKER)
        hist = ticker.history(
            start=start.strftime("%Y-%m-%d"),
            end=end.strftime("%Y-%m-%d"),
            progress=False,
        )
        if hist.empty:
            return None
        results = [
            {"date": idx.strftime("%Y-%m-%d"), "price": round(float(row["Close"]), 2)}
            for idx, row in hist.iterrows()
        ]
        logger.info("yfinance LIT trend: %d records", len(results))
        return results
    except Exception as exc:
        logger.debug("yfinance get_trend 失败: %s", exc)
        return None


# ── Tools ─────────────────────────────────────────────────

@mcp.tool()
async def get_price(commodity: str, date: str | None = None) -> float:
    """
    获取指定矿产在指定日期的价格（美元/吨）。

    优先级: yfinance LIT ETF → PriceSimulator 模拟

    Args:
        commodity: 矿产名称（如 lithium, copper, gold）
        date: 日期，格式 YYYY-MM-DD，不填则取最新
    """
    date = date or datetime.now().strftime("%Y-%m-%d")
    logger.info("[tool:get_price] commodity=%s, date=%s", commodity, date)

    yf_price = _try_yf_price(date)
    if yf_price is not None:
        return yf_price

    dt = datetime.strptime(date, "%Y-%m-%d")
    return _sim.get_price(commodity, dt)


@mcp.tool()
async def get_trend(commodity: str, days: int = 30) -> list[dict]:
    """
    获取指定矿产的近期价格趋势。

    优先级: yfinance LIT ETF → PriceSimulator 模拟

    Args:
        commodity: 矿产名称
        days: 回溯天数，默认 30

    Returns:
        [{"date": "YYYY-MM-DD", "price": float}, ...]  按日期升序
    """
    logger.info("[tool:get_trend] commodity=%s, days=%d", commodity, days)

    days = max(1, min(days, 365))  # 1-365 范围约束

    yf_trend = _try_yf_trend(days)
    if yf_trend is not None:
        return yf_trend

    return _sim.get_trend(commodity, days)


# ── 入口 ──────────────────────────────────────────────────

def main():
    logger.info("lme-price-mcp 启动中... (yfinance=%s)", "enabled" if _use_yf else "disabled")
    mcp.run(transport="stdio")


if __name__ == "__main__":
    main()
