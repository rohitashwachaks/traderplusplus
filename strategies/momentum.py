import pandas as pd

from core.context import DataContext
from strategies.base import TargetWeightStrategy, register


@register("momentum")
class Momentum(TargetWeightStrategy):
    """Single-asset moving-average crossover: hold the name (fully) while its short SMA is
    above its long SMA, otherwise sit in cash.

    This is a *per-name* rule. It is not meant to pool a basket — to judge it across a market
    you sweep it over the whole universe (one independent single-name run each) and read the
    distribution of alpha/beta, which is what makes it honest rather than a cherry-pick. See
    ``research/sweep.py``.

    **Reference:** Jegadeesh & Titman (1993). "Returns to Buying Winners and Selling Losers:
    Implications for Stock Market Efficiency." Journal of Finance.
    https://www.jstor.org/stable/2328882 — foundational work on momentum and trend-following.
    """

    name = "momentum"
    single_asset = True

    def __init__(self, short_window: int = 15, long_window: int = 30):
        if short_window >= long_window:
            raise ValueError("short_window must be < long_window")
        self.short_window = short_window
        self.long_window = long_window

    def weights(self, ctx: DataContext) -> pd.DataFrame:
        prices = ctx.price
        short_ma = prices.rolling(self.short_window).mean()
        long_ma = prices.rolling(self.long_window).mean()

        # 1.0 = fully in the name, 0.0 = cash. Each column is independent (single-asset rule).
        signal = (short_ma > long_ma).astype(float)
        signal = signal.where(ctx.members, 0.0)  # only hold while in the universe

        # Decide on day t's close, act on t+1 — this lag is what prevents look-ahead.
        return signal.shift(1).fillna(0.0)
