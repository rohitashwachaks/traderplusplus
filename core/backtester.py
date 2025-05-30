from core.executor import PortfolioExecutor
from typing import Dict, List
import pandas as pd

from core.guardrails.base import Guardrail


class Backtester:
    def __init__(self, strategy, data_loader, starting_cash=100000.0, guardrails: List[Guardrail] = None):
        self.strategy = strategy
        self.data_loader = data_loader
        self.executor = PortfolioExecutor(starting_cash=starting_cash, guardrails=guardrails)
        self.signals = {}
        self.market_data = {}
        self.symbols = []
        self.start_date = None
        self.end_date = None

    def run(self, symbols: List[str], start_date: str, end_date: str):
        self.symbols = symbols
        self.start_date = start_date
        self.end_date = end_date

        # Load data once
        self.market_data = {
            symbol: self.data_loader(symbol, start_date, end_date)
            for symbol in symbols
        }

        # Align index
        common_index = self.market_data[symbols[0]].index
        for sym in self.market_data:
            self.market_data[sym] = self.market_data[sym].reindex(common_index).ffill()

        # Precompute signals
        self.signals = self.strategy.generate_signals(self.market_data)

        for current_date in common_index:
            # Extract closing prices for current date
            prices = {
                symbol: df.loc[current_date, 'Close']
                for symbol, df in self.market_data.items()
                if current_date in df.index
            }

            # Allocate shares
            allocations = self.strategy.generate_allocations(
                signals={s: df.loc[[current_date]] for s, df in self.signals.items()},
                portfolio_cash=self.executor.cash,
                market_data={s: df.loc[[current_date]] for s, df in self.market_data.items()}
            )

            self.executor.execute_trades(current_date, allocations, prices)
            self.executor.update_equity(current_date, prices)

    def get_trade_log(self) -> pd.DataFrame:
        return self.executor.get_trade_log()

    def get_equity_curve(self) -> pd.DataFrame:
        return self.executor.get_equity_curve()

    def get_final_net_worth(self) -> float:
        return self.get_equity_curve()['net_worth'].iloc[-1]

    def get_market_data(self) -> Dict[str, pd.DataFrame]:
        return self.market_data
