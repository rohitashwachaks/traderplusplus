from abc import ABC

import pandas as pd
from typing import Dict

from contracts.asset import Asset, CashAsset
from core.market_data import MarketData
from strategies.stock.base import StrategyBase, StrategyFactory


@StrategyFactory.register("momentum")
class MomentumStrategy(StrategyBase, ABC):
    def __init__(self, short_window: int = 10, long_window: int = 20, lookback_window: int = 60, **kwargs):
        self.short_window = short_window
        self.long_window = long_window
        self.lookback_window = lookback_window

    def get_name(self) -> str:
        return f"momentum_{self.short_window}_{self.long_window}"

    def get_config(self) -> Dict:
        return {
            "type": "momentum",
            "short_window": self.short_window,
            "long_window": self.long_window,
            "name": self.get_name()
        }

    def generate_signals(self, market_data: MarketData, current_date: pd.Timestamp,
                         positions: Dict[str, Asset | CashAsset], cash) -> Dict[str, int]:
        """
        Generate signals for all tickers based on moving average crossover.
        :param cash:
        """
        signals = {}
        cash_per_asset = positions['CASH'].shares / len([ticker for ticker in positions if isinstance(positions[ticker], Asset)])
        for ticker in market_data.get_available_symbols():
            # history = market_data.get_history(ticker, end_date=current_date, lookback=self.lookback_window)
            history = market_data.get_history(ticker, end_date=current_date, lookback=self.long_window+1)

            # Ensure we have enough data for both short and long moving averages
            if history.empty or len(history) < self.long_window:
                continue

            short_ma = history['Close'].rolling(window=self.short_window, min_periods=1).mean()
            long_ma = history['Close'].rolling(window=self.long_window, min_periods=1).mean()

            # Crossover logic
            if short_ma.iloc[-2] <= long_ma.iloc[-2] and short_ma.iloc[-1] > long_ma.iloc[-1]:
                # Buy signal: short MA crosses above long MA
                signals[ticker] = cash_per_asset // market_data.get_price(ticker, current_date)
            elif short_ma.iloc[-2] >= long_ma.iloc[-2] and short_ma.iloc[-1] < long_ma.iloc[-1]:
                # Sell signal: short MA crosses below long MA
                signals[ticker] = -positions[ticker].shares
            else:
                # Hold: no signal
                continue

        return signals
