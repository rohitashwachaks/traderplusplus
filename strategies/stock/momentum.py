import pandas as pd
from strategies.stock.base import StrategyBase, StrategyFactory


@StrategyFactory.register("momentum")
class MomentumStrategy(StrategyBase):
    """Basic momentum breakout strategy using moving average crossover."""

    def __init__(self, short_window: int = 10, long_window: int = 30):
        self.short_window = short_window
        self.long_window = long_window

    def get_name(self) -> str:
        return f"Momentum_{self.short_window}_{self.long_window}"

    def generate_signals(self, data: pd.DataFrame) -> pd.DataFrame:
        signals = data.copy()
        signals['short_ma'] = data['Close'].rolling(window=self.short_window).mean()
        signals['long_ma'] = data['Close'].rolling(window=self.long_window).mean()

        signals['signal'] = 0
        signals['signal'][self.long_window:] = (
                signals['short_ma'][self.long_window:] > signals['long_ma'][self.long_window:]
        ).astype(int)

        signals['position'] = signals['signal'].diff()
        return signals
