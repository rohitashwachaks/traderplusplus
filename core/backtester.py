from typing import List, Dict
import pandas as pd

from strategies.stock.base import StrategyBase


class BacktestResult:
    def __init__(self, strategy_name: str, symbol: str, trades: pd.DataFrame, equity_curve: pd.Series):
        self.strategy_name = strategy_name
        self.symbol = symbol
        self.trades = trades
        self.equity_curve = equity_curve


class Backtester:
    def __init__(self, data_loader):
        self.data_loader = data_loader
        self.results: List[BacktestResult] = []

    def run(self, strategies: Dict[str, StrategyBase], symbols: List[str], start_date: str, end_date: str):
        for symbol in symbols:
            df = self.data_loader(symbol, start_date, end_date)
            for strat_name, strategy in strategies.items():
                signals = strategy.generate_signals(df)
                trades, equity = self._simulate_trades(signals)
                self.results.append(BacktestResult(strat_name, symbol, trades, equity))

    def _simulate_trades(self, df: pd.DataFrame):
        """Simulate trade logic: Buy at signal == 1, Sell at signal == 0"""
        position = 0
        trades = []
        equity = []

        for i in range(1, len(df)):
            if df['position'].iloc[i] == 1:  # Buy signal
                buy_price = df['Close'].iloc[i]
                position = buy_price
                trades.append({'type': 'BUY', 'date': df.index[i], 'price': buy_price})

            elif df['position'].iloc[i] == -1 and position > 0:  # Sell signal
                sell_price = df['Close'].iloc[i]
                pnl = sell_price - position
                trades.append({'type': 'SELL', 'date': df.index[i], 'price': sell_price, 'pnl': pnl})
                position = 0

            equity.append(position if position > 0 else 0)

        return pd.DataFrame(trades), pd.Series(equity, index=df.index[:len(equity)])

    def get_results(self) -> List[BacktestResult]:
        return self.results

    def summarize_portfolio(self):
        """Aggregate all equity curves to a single portfolio view."""
        all_curves = [res.equity_curve for res in self.results]
        df = pd.concat(all_curves, axis=1).fillna(0)
        df['total'] = df.sum(axis=1)
        return df['total']
