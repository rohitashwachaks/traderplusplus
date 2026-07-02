import numpy as np
import pandas as pd

from guardrails.base import Guardrail, register


@register("stop_loss")
class StopLoss(Guardrail):
    """Force a ticker to cash after it falls ``pct`` from its reference price.

    Reference is the peak since entry (``trailing=True``) or the entry price
    (``trailing=False``). Because we only have daily bars, the breach is measured on a
    day's close and the exit takes effect on the **next** close — no intraday or
    optimistic stop-price fills. After a stop-out the ticker stays out (latched) until the
    strategy itself goes flat on it and re-enters, which avoids day-after thrashing. Freed
    weight goes to cash; it is not redistributed to other holdings.
    """

    name = "stop_loss"

    def __init__(self, pct: float = 0.05, trailing: bool = True):
        if not 0 < pct < 1:
            raise ValueError("pct must be in (0, 1), e.g. 0.05 for a 5% stop")
        self.pct = pct
        self.trailing = trailing

    def apply(self, prices: pd.DataFrame, weights: pd.DataFrame) -> pd.DataFrame:
        # Do NOT reindex prices — we need the full daily history to detect intramonth crashes.
        # The stop-loss logic runs on daily prices, but we only return adjusted weights at the
        # dates where the strategy defined them.
        keep = pd.DataFrame(1.0, index=prices.index, columns=weights.columns)
        for ticker in weights.columns:
            keep[ticker] = self._keep(prices[ticker].to_numpy(),
                                       weights.reindex(prices.index).fillna(0.0)[ticker].to_numpy() > 0)
        # The breach is seen at close t; the exit lands on t+1 — no look-ahead.
        keep = keep.shift(1).fillna(1.0)
        # Return adjusted weights, reindexed back to the strategy's weight dates.
        return (weights.reindex(prices.index).fillna(0.0) * keep).reindex(weights.index)

    def _keep(self, price: np.ndarray, want: np.ndarray) -> np.ndarray:
        """Per-ticker 'allowed to hold' mask in as-of-close-``t`` terms (shifted by the
        caller). ``want[t]`` is whether the strategy intends to hold on day ``t``."""
        keep = np.ones(len(price))
        holding = False
        latched = False
        ref = np.nan
        for t in range(len(price)):
            if latched:
                if want[t]:
                    keep[t] = 0.0
                    continue
                latched = False  # strategy exited on its own → release the latch
            if holding:
                if self.trailing and price[t] > ref:
                    ref = price[t]
                if price[t] <= ref * (1 - self.pct):
                    keep[t] = 0.0
                    holding = False
                    latched = True
            elif want[t]:
                holding = True
                ref = price[t]
        return keep
