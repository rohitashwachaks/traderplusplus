import pandas as pd
import yfinance as yf
from typing import Dict, List, Optional

from contracts.asset import Asset, CashAsset
from contracts.order import Order
from utils.utils import clean_ticker
from guardrails.base import GuardrailFactory
from strategies.base import StrategyBase, StrategyFactory


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
                 guardrail: Optional[str] = None,
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
            guardrail (str, optional): GuardrailBase strategy to apply (e.g., 'trailing_stop_loss').
            rebalance_freq (str, optional): Rebalancing frequency (e.g., 'monthly', 'quarterly', 'annually').
            recomposition_freq (str, optional): Frequency for recomposition (e.g., 'monthly', 'quarterly', 'annually').
            metadata (Dict, optional): Additional metadata.
        """
        # Initialize Portfolio name
        assert (isinstance(name, str) and name.strip()), "Portfolio name must be a non-empty string"
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

        # Initialize guardrail
        if guardrail:
            assert guardrail in GuardrailFactory.get_supported_guardrails(), f"Unsupported guardrail: {guardrail}. Supported guardrails: {GuardrailFactory.get_supported_guardrails()}"
            self.guardrail = GuardrailFactory.create_guardrail(guardrail)

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

    def execute_trade(self, date: pd.Timestamp, order: Order, price: float,
                      note: str = 'Strategy Signal'):
        """
        Execute a trade and update portfolio positions and cash.

        Args:
            date (pd.Timestamp): Trade date.
            price (float): Trade price per share.
            order (Order): Order object containing trade details.
            note (str): Optional trade note.
        Raises:
            ValueError: If insufficient cash or shares.
        """
        ticker = order.ticker
        action = order.side.name
        shares = order.quantity
        trade_value = shares * price
        if action == 'BUY':
            if self.cash < trade_value:
                raise ValueError(f"Insufficient cash to buy {shares} shares of {ticker}")
        elif action == 'SELL':
            held = self.get_position(ticker)
            if held < shares:
                raise ValueError(f"Trying to sell more shares than held for {ticker}")
        else:
            raise ValueError("Action must be either 'BUY' or 'SELL'")

        self.update_position(ticker, shares, action, trade_value)
        self.add_trade(date, ticker, action, shares, price, self._cash.shares, note)

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

    # region Get Methods

    def update_position(self, ticker, shares_delta: int, action: str, trade_value: float):
        if ticker not in self._positions:
            raise ValueError(f"Unknown ticker {ticker}")
        if action == 'BUY':
            self._cash.withdraw_cash(trade_value)
            self._positions[ticker].buy(shares_delta)
        elif action == 'SELL':
            self._positions[ticker].sell(shares_delta)
            self._cash.deposit_cash(trade_value)

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
        if ticker not in self._positions:
            return 0
        return self._positions[ticker].shares

    def net_worth(self, prices: Dict[str, float]) -> float:
        """
        Compute total portfolio value given current prices.
        Args:
            prices (Dict[str, float]): Mapping of ticker to price.
        Returns:
            float: Total portfolio value.
        """
        value = self.cash
        for ticker in self.tickers:
            value += self._positions[ticker].shares * prices[ticker]
        return value
    # endregion Get Methods

    # region Properties

    @property
    def cash(self) -> float:
        """
        Get the current cash shares in the portfolio.
        Returns:
            float: Current cash shares.
        """
        return self._cash.shares

    @property
    def positions(self) -> dict:
        """
        Get the current positions in the portfolio.
        Returns:
            dict: Dictionary of asset ticker to Asset object.
        """
        return self._positions

    # endregion Properties
