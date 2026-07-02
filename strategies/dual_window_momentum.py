import pandas as pd

from core.context import DataContext
from strategies.base import TargetWeightStrategy, register


@register("dual_momentum")
class DualWindowMomentum(TargetWeightStrategy):
    """Rank a basket by dual-window momentum (short-term minus long-term returns).

    Identifies stocks with *accelerating* momentum: computes the return over a short lookback
    and a long lookback, then ranks by (short - long). This separates stocks with upward-
    accelerating momentum from those rising but decelerating. Holds the top names equal-weighted.

    Meant for a basket of tickers — with one or two names it degenerates. Defaults to a monthly
    rebalance/reconstitution (override via the strategy's freq attributes or the CLI).

    **Reference:** Moskowitz & Grinblatt (2000). "Do Industries Explain Momentum?" Journal of
    Finance. https://www.jstor.org/stable/2329335 — studies short-term (3–12 month) vs.
    long-term momentum. Jegadeesh & Titman (2001). "Profitability of Momentum Strategies: An
    Evaluation of Alternative Explanations." https://www.jstor.org/stable/2329370 — shows that
    intermediate-term relative strength (short beating long) is a robust signal of momentum.
    """

    name = "dual_momentum"
    rebalance_freq = "M"
    reconstitution_freq = "M"

    def __init__(self, short_window: int = 20, long_window: int = 120, top_n: int | None = None):
        if short_window < 1:
            raise ValueError("short_window must be >= 1")
        if long_window < 1:
            raise ValueError("long_window must be >= 1")
        if short_window >= long_window:
            raise ValueError("short_window must be < long_window")
        if top_n is not None and top_n < 1:
            raise ValueError("top_n must be >= 1 or None")
        self.short_window = short_window
        self.long_window = long_window
        self.top_n = top_n

    def weights(self, ctx: DataContext) -> pd.DataFrame:
        prices = ctx.price.where(ctx.members)  # rank only among in-universe names
        short_momentum = prices.pct_change(self.short_window)
        long_momentum = prices.pct_change(self.long_window)

        # Dual-window score: compare the *per-day rate* of each window, not the raw cumulative
        # returns (the long window spans more days, so its total return would otherwise dominate).
        # Positive score = recent pace exceeds long-run pace = accelerating momentum.
        score = short_momentum / self.short_window - long_momentum / self.long_window
        n = self.top_n or max(1, prices.shape[1] // 2)

        ranks = score.rank(axis=1, ascending=False, method="first")
        selected = ranks.le(n) & score.notna()
        count = selected.sum(axis=1)
        weights = selected.div(count.where(count > 0), axis=0).fillna(0.0)

        # Decide on day t's close, act on t+1 — this lag is what prevents look-ahead.
        return weights.shift(1).fillna(0.0)
