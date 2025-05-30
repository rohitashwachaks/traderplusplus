import pandas as pd
from typing import Dict

from strategies.stock.base import StrategyBase, StrategyFactory


@StrategyFactory.register("momentum")
class MomentumStrategy(StrategyBase):
    def __init__(self, short_window: int = 15, long_window: int = 30):
        self.short_window = short_window
        self.long_window = long_window

    def get_name(self) -> str:
        return f"momentum_{self.short_window}_{self.long_window}"

    def generate_signals(self, market_data: Dict[str, pd.DataFrame]) -> Dict[str, pd.DataFrame]:
        signal_dict = {}

        for symbol, df in market_data.items():
            df = df.copy()

            # Moving averages
            df['short_ma'] = df['Close'].rolling(window=self.short_window, min_periods=1).mean()
            df['long_ma'] = df['Close'].rolling(window=self.long_window, min_periods=1).mean()

            # Buy: short MA crosses above long MA
            df['buy_signal'] = (
                    (df['short_ma'].shift(1) <= df['long_ma'].shift(1)) &
                    (df['short_ma'] > df['long_ma'])
            )

            # Sell: short MA crosses below long MA
            df['sell_signal'] = (
                    (df['short_ma'].shift(1) >= df['long_ma'].shift(1)) &
                    (df['short_ma'] < df['long_ma'])
            )

            # Position: +1 (buy), -1 (sell), 0 (hold)
            df['position'] = 0
            df.loc[df['buy_signal'], 'position'] = 1
            df.loc[df['sell_signal'], 'position'] = -1

            signal_dict[symbol] = df

        return signal_dict

    def generate_allocations(
            self,
            signals: Dict[str, pd.DataFrame],
            portfolio_cash: float,
            market_data: Dict[str, pd.DataFrame]
    ) -> Dict[str, int]:
        allocations = {}

        for symbol, signal_df in signals.items():
            signal = signal_df['position'].iloc[-1]
            price = market_data[symbol]['Close'].iloc[-1]

            if signal == 1:  # Buy signal
                allocation = int((portfolio_cash / len(signals)) // price)
                if allocation > 0:
                    allocations[symbol] = allocation

            elif signal == -1:  # Sell signal
                allocations[symbol] = -1  # signal to sell full position

        return allocations
