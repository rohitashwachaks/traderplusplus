import pandas as pd
import yfinance as yf
from typing import Dict, List, Optional

from contracts.asset import Asset, CashAsset
from contracts.utils import clean_ticker
from strategies.stock.base import StrategyBase, StrategyFactory


class Portfolio:
    """
    Portfolio manages asset and cash positions, executes trades, and logs portfolio history.
    It does not handle analytics or performance evaluation directly.
    """
    def __init__(self,
                 name: str,
                 tickers: str | List[str],
                 starting_cash: float,
                 strategy: str,
                 benchmark: str = "SPY",
                 rebalance_freq: Optional[str] = None,
                 recomposition_freq: Optional[str] = None,
                 metadata: Dict = None):
        """
        Initialize a Portfolio object.

        Args:
            name (str): Name of the portfolio.
            tickers (List[str]): List of asset tickers.
            starting_cash (float): Initial cash shares.
            strategy (StrategyBase): Strategy instance to generate signals.
            benchmark (str): Benchmark ticker for reference only.
            rebalance_freq (str, optional): Rebalancing frequency (e.g., 'monthly', 'quarterly', 'annually').
            recomposition_freq (str, optional): Frequency for recomposition (e.g., 'monthly', 'quarterly', 'annually').
            metadata (Dict, optional): Additional metadata.
        """
        # Initialize Portfolio name
        assert (isinstance(name, str) and not name.strip()), "Portfolio name must be a non-empty string"
        self.name = name

        # Initialize tickers
        if isinstance(tickers, str):
            tickers = [clean_ticker(ticker) for ticker in tickers.split(",")]
        assert isinstance(tickers, list), "tickers must be a list or comma-separated string"
        self.tickers = tickers

        # Initialize strategy
        assert strategy in StrategyFactory.get_supported_strategies(), f"Unsupported strategy: {strategy}. Supported strategies: {StrategyFactory.get_supported_strategies()}"
        self.strategy = StrategyFactory.create_strategy(strategy)

        # Initialise benchmark
        benchmark = clean_ticker(benchmark)
        assert isinstance(benchmark, str), "Benchmark must be a string"
        self.benchmark = benchmark

        self._positions: Dict[str, Asset | CashAsset] = {
            ticker: Asset(ticker)
            for ticker in tickers
        }
        self._cash = CashAsset(starting_cash)

        self.trade_log: List[dict] = []
        self.position_history: Dict[str, List[int]] = {}

        self.rebalance_freq = rebalance_freq
        self.recomposition_freq = recomposition_freq
        self.metadata = metadata or {}

    def execute_trade(self, date: pd.Timestamp, ticker: str,
                      action: str, shares: int, price: float,
                      note: str = 'Strategy Signal'):
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

        if action == 'BUY':
            if self.cash < trade_value:
                raise ValueError(f"Insufficient cash to buy {shares} shares of {ticker}")
            self._cash.withdraw_cash(trade_value)
            self.update_position(ticker, shares)

        elif action == 'SELL':
            held = self.get_position(ticker)
            if held < shares:
                raise ValueError(f"Trying to sell more shares than held for {ticker}")
            self.update_position(ticker, -shares)
            self._cash.deposit_cash(trade_value)

        else:
            raise ValueError("Action must be either 'BUY' or 'SELL'")

        self.add_trade(date, ticker, action, shares, price, self._cash.shares, note)

    def get_cash(self) -> float:
        return self.positions['CASH'].shares

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

    # region Properties

    @property
    def cash(self) -> float:
        """
        Get the current cash shares in the portfolio.
        Returns:
            float: Current cash shares.
        """
        return self.positions['CASH'].shares

    @property
    def positions(self) -> dict:
        """
        Get the current positions in the portfolio.
        Returns:
            dict: Dictionary of asset ticker to Asset object.
        """
        return self.positions

    # endregion Properties
