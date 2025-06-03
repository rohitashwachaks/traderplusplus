from typing import Dict, List

import pandas as pd

from contracts.asset import Asset, CashAsset
from strategies.stock.base import StrategyBase


class Portfolio:
    """
    Portfolio manages asset and cash positions, executes trades, and logs portfolio history.
    It does not handle analytics or performance evaluation directly.
    """
    def __init__(self,
                 name: str,
                 tickers: List[str],
                 starting_cash: float,
                 strategy: StrategyBase,
                 benchmark: str = "SPY",
                 rebalance_freq: str = "monthly",
                 metadata: Dict = None):
        """
        Initialize a Portfolio object.

        Args:
            name (str): Name of the portfolio.
            tickers (List[str]): List of asset tickers.
            starting_cash (float): Initial cash balance.
            strategy (StrategyBase): Strategy instance to generate signals.
            benchmark (str): Benchmark ticker for reference only.
            rebalance_freq (str): Rebalancing frequency (e.g., 'monthly').
            metadata (Dict, optional): Additional metadata.
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
        self.trade_log: List[dict] = []
        self.position_history: Dict[str, List[int]] = {}

    def execute_trade(self, date: pd.Timestamp, ticker: str, action: str, shares: int, price: float, note: str = 'Strategy Signal'):
        """
        Execute a trade and update portfolio positions and cash.

        Args:
            date (pd.Timestamp): Trade date.
            ticker (str): Asset ticker.
            action (str): 'BUY' or 'SELL'.
            shares (int): Number of shares.
            price (float): Trade price per share.
            note (str): Optional trade note.
        Raises:
            ValueError: If insufficient cash or shares.
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

    def get_trade_log(self) -> pd.DataFrame:
        df = pd.DataFrame(self.trade_log)
        if not df.empty:
            df['date'] = pd.to_datetime(df['date'])
            df.set_index('date', inplace=True)
            df = df.sort_index()
        else:
            df = pd.DataFrame(columns=['date', 'ticker', 'action', 'shares', 'price', 'cash_remaining', 'note'])
        return df

    def get_position(self, ticker) -> int:
        if ticker not in self.positions:
            return 0
        return self.positions[ticker].shares

    def get_portfolio_value(self, prices: Dict[str, float]) -> float:
        """
        Compute total portfolio value given current prices.
        Args:
            prices (Dict[str, float]): Mapping of ticker to price.
        Returns:
            float: Total portfolio value.
        """
        value = self.get_cash()
        for ticker in self.tickers:
            value += self.positions[ticker].shares * prices.get(ticker, 0.0)
        return value
