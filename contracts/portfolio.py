from typing import Dict, List

import pandas as pd

from analytics.performance import evaluate_portfolio_performance
from contracts.asset import Asset, CashAsset
from strategies.stock.base import StrategyBase


class Portfolio:
    def __init__(self,
                 name: str,
                 tickers: List[str],
                 starting_cash: float,
                 strategy: StrategyBase,
                 benchmark: str = "^SPY",
                 rebalance_freq: str = "monthly",
                 metadata: Dict = None):
        """
        Initialize a Portfolio object with strategy, tickers, and starting cash.

        :param name: Name of the portfolio
        :param tickers: List of tickers in the portfolio
        :param starting_cash: Initial cash in the portfolio
        :param strategy: Strategy object associated with this portfolio
        :param benchmark: Benchmark ticker used to compare portfolio performance (e.g., ^SPY)
        :param rebalance_freq: Frequency of rebalancing (e.g., monthly, quarterly)
        :param metadata: Additional metadata or user-defined attributes
        """
        self.name = name
        self.tickers = tickers
        self.strategy = strategy
        self.benchmark = benchmark
        self.rebalance_freq = rebalance_freq
        self.metadata = metadata or {}

        self.positions: Dict[str, Asset | CashAsset] = {
            ticker: Asset(ticker)
            for ticker in tickers
        }
        self.positions['CASH'] = CashAsset(starting_cash)
        self.trade_log = []
        self.position_history: Dict[str, List[int]] = {}

    def execute_trade(self, date, ticker, action, shares, price, note='Strategy Signal'):
        """
        Executes a trade and adjusts portfolio cash and position accordingly.

        :param date: Trade date
        :param ticker: Ticker symbol
        :param action: 'BUY' or 'SELL'
        :param shares: Number of shares
        :param price: Trade price per share
        :param note: Optional note (e.g., 'Strategy Signal')
        """
        trade_value = shares * price
        cash_asset = self.positions['CASH']

        if action == 'BUY':
            if cash_asset.balance < trade_value:
                raise ValueError(f"Insufficient cash to buy {shares} shares of {ticker}")
            cash_asset.withdraw_cash(trade_value)
            self.update_position(ticker, shares)

        elif action == 'SELL':
            held = self.get_position(ticker)
            if held < shares:
                raise ValueError(f"Trying to sell more shares than held for {ticker}")
            self.update_position(ticker, -shares)
            cash_asset.deposit_cash(trade_value)

        else:
            raise ValueError("Action must be either 'BUY' or 'SELL'")

        self.add_trade(date, ticker, action, shares, price, cash_asset.balance, note)

    def get_cash(self) -> float:
        return self.positions['CASH'].balance

    def add_trade(self, date, ticker, action, shares, price, cash_remaining, note=''):
        entry = {
            'date': date,
            'ticker': ticker,
            'action': action,
            'shares': shares,
            'price': price,
            'cash_remaining': cash_remaining,
            'note': note
        }
        if action == 'BUY':
            entry['cost'] = shares * price
        elif action == 'SELL':
            entry['revenue'] = shares * price
        self.trade_log.append(entry)

    def update_position(self, ticker, shares_delta):
        if ticker not in self.positions:
            self.positions[ticker] = Asset(ticker)
        if shares_delta > 0:
            self.positions[ticker].buy(shares_delta)
        elif shares_delta < 0:
            self.positions[ticker].sell(abs(shares_delta))
        if self.positions[ticker].is_empty():
            del self.positions[ticker]

    def get_trade_log(self) -> pd.DataFrame:
        return pd.DataFrame(self.trade_log)

    def get_position(self, ticker) -> int:
        if ticker not in self.positions:
            return 0
        return self.positions[ticker].shares

    def evaluate_performance(self, benchmark_data: pd.DataFrame) -> Dict[str, float]:
        """
        Evaluate portfolio performance using trade logs and benchmark returns.

        :param benchmark_data: DataFrame with 'Close' prices indexed by date
        :return: Dictionary with performance metrics like Sharpe ratio and Alpha
        """
        return evaluate_portfolio_performance(self.get_trade_log(), benchmark_data)
