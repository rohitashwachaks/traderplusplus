from abc import ABC

import pandas as pd
from typing import Dict

from core.market_data import MarketData
from strategies.stock.base import StrategyBase, StrategyFactory


@StrategyFactory.register("momentum")
class MomentumStrategy(StrategyBase, ABC):
    def __init__(self, short_window: int = 10, long_window: int = 20):
        self.short_window = short_window
        self.long_window = long_window

    def get_name(self) -> str:
        return f"momentum_{self.short_window}_{self.long_window}"

    def get_config(self) -> Dict:
        return {
            "type": "momentum",
            "short_window": self.short_window,
            "long_window": self.long_window,
            "name": self.get_name()
        }

    def generate_signals(
        self,
        market_data: MarketData,
        current_date: pd.Timestamp,
        lookback_window: int = 60
    ) -> Dict[str, int]:
        """
        Generate signals for all tickers based on moving average crossover.
        """
        signals = {}
        for ticker in market_data.get_available_symbols():
            history = market_data.get_history(ticker, end_date=current_date, lookback=lookback_window)
            if len(history) < self.long_window:
                signals[ticker] = 0
                continue

            short_ma = history['Close'].rolling(window=self.short_window, min_periods=1).mean()
            long_ma = history['Close'].rolling(window=self.long_window, min_periods=1).mean()

            # Crossover logic
            if short_ma.iloc[-2] <= long_ma.iloc[-2] and short_ma.iloc[-1] > long_ma.iloc[-1]:
                signals[ticker] = 1  # Buy
            elif short_ma.iloc[-2] >= long_ma.iloc[-2] and short_ma.iloc[-1] < long_ma.iloc[-1]:
                signals[ticker] = -1  # Sell
            else:
                signals[ticker] = 0  # Hold

        return signals
