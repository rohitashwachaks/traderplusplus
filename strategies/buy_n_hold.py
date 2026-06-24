import pandas as pd

from strategies.base import TargetWeightStrategy, register


@register("buy_n_hold")
class BuyAndHold(TargetWeightStrategy):
    """Allocate equally across all tickers on day one and hold. Constant target weights,
    so the engine buys once and never trades again."""

    name = "buy_n_hold"

    def weights(self, prices: pd.DataFrame) -> pd.DataFrame:
        weight = 1.0 / prices.shape[1]
        return pd.DataFrame(weight, index=prices.index, columns=prices.columns)
