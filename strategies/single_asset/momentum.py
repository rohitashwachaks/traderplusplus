from abc import ABC

import pandas as pd
from typing import Dict, Optional

from contracts.asset import Asset, CashAsset
from core.market_data import MarketData
from strategies.base import StrategyBase, StrategyFactory


@StrategyFactory.register("momentum")
class MomentumStrategy(StrategyBase, ABC):
    def __init__(self, short_window: int = 3, long_window: int = 10, lookback_period: int = 10, **kwargs):
        self.short_window = short_window
        self.long_window = long_window
        self.lookback_period = lookback_period

    def get_name(self) -> str:
        return f"momentum_{self.short_window}_{self.long_window}"

    def get_config(self) -> Dict:
        return {
            "type": "momentum",
            "short_window": self.short_window,
            "long_window": self.long_window,
            "name": self.get_name()
        }

    def generate_signals(self, price_data: pd.DataFrame | Dict[str, pd.DataFrame],
                         current_date: pd.Timestamp, positions: Dict[str, Asset],
                         cash: float, **kwargs) -> Optional[Dict[str, int]]:
        """
        Generate signals for all tickers based on moving average crossover.
        :param price_data:
        :param current_date:
        :param positions:
        :param cash:
        """
        signals: Optional[Dict[str, int]] = {}

        ticker = list(positions.keys())[0]  # Single ticker strategy

        # Ensure we have enough data for both short and long moving averages
        if price_data is None or len(price_data[ticker]) < self.long_window:
            return

        short_ma = price_data[ticker]['Close'].rolling(window=self.short_window, min_periods=1).mean()
        long_ma = price_data[ticker]['Close'].rolling(window=self.long_window, min_periods=1).mean()

        # Crossover logic
        if short_ma.iloc[-2] <= long_ma.iloc[-2] and short_ma.iloc[-1] > long_ma.iloc[-1]:
            # Buy signal: short MA crosses above long MA
            signals[ticker] = int(cash / price_data[ticker]['Close'].loc[current_date])
        elif short_ma.iloc[-2] >= long_ma.iloc[-2] and short_ma.iloc[-1] < long_ma.iloc[-1]:
            # Sell signal: short MA crosses below long MA
            signals[ticker] = -positions[ticker].shares
        else:
            # Hold: no signal
            signals = None

        return signals
