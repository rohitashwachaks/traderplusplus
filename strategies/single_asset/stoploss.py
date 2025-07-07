from abc import ABC
from typing import Dict, Optional

import pandas as pd

from contracts.asset import Asset, CashAsset
from core.market_data import MarketData
from strategies.base import StrategyBase, StrategyFactory


@StrategyFactory.register("stoploss")
class StoplossStrategy(StrategyBase, ABC):
    def __init__(self, **kwargs):
        self.lookback_period = 20
        self.has_bought: Optional[float] = None
        self.trail_pct: float = kwargs.get("trail_pct", 0.07)

    def get_name(self) -> str:
        return "stoploss"

    def get_config(self) -> Dict:
        return {
            "type": self.get_name()
        }

    def generate_signals(self, price_data: pd.DataFrame | Dict[str, pd.DataFrame], current_date: pd.Timestamp,
                         positions: Dict[str, Asset], cash: float, **kwargs) -> Optional[Dict[str, int]]:
        """
        Buy once and hold till perpetuity for the strategy.
        :param price_data: A DataFrame or dict of DataFrames containing price data for each asset.
        :param cash:
        :param current_date:
        :param positions:
        :return:
        """
        ticker = list(positions.keys())[0]  # Single ticker strategy
        signals = {}

        if self.has_bought:
            # If already bought, SELL if cur_price lower than trailing stop-loss
            cur_price = price_data[ticker]['Close'].loc[current_date]
            if cur_price < (self.has_bought * (1-self.trail_pct)):
                # SELL
                signals[ticker] = -positions[ticker].shares
                self.has_bought = None
            elif cur_price > self.has_bought:
                self.has_bought = cur_price

        else:
            try:
                pct_change = price_data[ticker]['Close'].pct_change().dropna()
                avg_pct_change = pct_change.mean()
                cur_pct_change = pct_change[-int(self.lookback_period/2):].mean()
                if cur_pct_change > 0 and cur_pct_change > avg_pct_change:
                    cur_price = price_data[ticker]['Close'].loc[current_date]
                    signals[ticker] = int(cash / cur_price)
                    self.has_bought = cur_price
            except Exception as e:
                print('here')

        return signals
