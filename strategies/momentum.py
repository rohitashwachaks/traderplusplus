import pandas as pd

from strategies.base import TargetWeightStrategy, register


@register("momentum")
class Momentum(TargetWeightStrategy):
    """Moving-average crossover. Hold a ticker (equal weight among those held) while its
    short SMA is above its long SMA, otherwise stay in cash for that ticker."""

    name = "momentum"

    def __init__(self, short_window: int = 3, long_window: int = 10):
        if short_window >= long_window:
            raise ValueError("short_window must be < long_window")
        self.short_window = short_window
        self.long_window = long_window

    def weights(self, prices: pd.DataFrame) -> pd.DataFrame:
        short_ma = prices.rolling(self.short_window).mean()
        long_ma = prices.rolling(self.long_window).mean()

        # 1 where in the market, 0 where in cash; split equally across held tickers.
        signal = (short_ma > long_ma).astype(float)
        held = signal.sum(axis=1)
        weights = signal.div(held.where(held > 0), axis=0).fillna(0.0)

        # Decide on day t's close, act on t+1 — this lag is what prevents look-ahead.
        return weights.shift(1).fillna(0.0)
