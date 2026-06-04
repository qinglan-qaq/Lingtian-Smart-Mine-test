"""
价格模拟器 — 确定性伪随机价格生成。

使用 hash(commodity + date) 作为种子，确保同一输入永远输出相同结果。
"""

import random
from datetime import datetime, timedelta


class PriceSimulator:
    """
    矿产价格模拟器。

    用法:
        sim = PriceSimulator(base_price=1200.0)
        price = sim.get_price("lithium", datetime(2026, 6, 1))
        trend = sim.get_trend("lithium", days=30)
    """

    def __init__(
        self,
        base_price: float = 1200.0,
        trend_per_day: float = 0.02,
        volatility: float = 15.0,
        base_date: datetime = datetime(2026, 1, 1),
    ):
        self.base_price = base_price
        self.trend_per_day = trend_per_day
        self.volatility = volatility
        self.base_date = base_date

    def get_price(self, commodity: str, date: datetime) -> float:
        """
        生成确定性模拟价格。

        以 commodity + date 的 hash 为随机种子，叠加趋势+噪声。
        价格不会为负，四舍五入到两位小数。
        """
        seed = abs(hash(f"{commodity}_{date.strftime('%Y%m%d')}")) % (10 ** 9)
        rng = random.Random(seed)

        # 趋势分量：距基准日期的天数 × 每日趋势
        days_since_base = (date - self.base_date).days
        trend = self.trend_per_day * days_since_base

        # 高斯噪声
        noise = rng.gauss(0, self.volatility)

        price = self.base_price + trend + noise
        price = max(price, 0.01)  # 不允许负价格
        return round(price, 2)

    def get_trend(self, commodity: str, days: int) -> list[dict]:
        """
        生成过去 N 天的价格序列。

        Returns:
            [{"date": "YYYY-MM-DD", "price": float}, ...]  日期从远到近排列
        """
        today = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
        results = []
        for i in range(days - 1, -1, -1):
            d = today - timedelta(days=i)
            price = self.get_price(commodity, d)
            results.append({"date": d.strftime("%Y-%m-%d"), "price": price})
        return results
