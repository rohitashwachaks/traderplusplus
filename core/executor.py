import pandas as pd
from typing import Dict, List

from core.guardrails.base import Guardrail
from core.market_data import MarketData
from contracts.portfolio import Portfolio


class PortfolioExecutor:
    """
    Executes portfolio trades using its associated strategy, manages guardrails, and tracks equity curve and trade log.
    """
    def __init__(
        self,
        portfolio: Portfolio,
        market_data: MarketData,
        guardrails: List[Guardrail] = None
    ):
        """
        Initializes the PortfolioExecutor.

        Args:
            portfolio (Portfolio): The portfolio object to manage.
            market_data (MarketData): Market data access object.
            guardrails (List[Guardrail], optional): List of guardrail objects. Defaults to None.
        """
        self.portfolio = portfolio
        self.market_data = market_data
        self.guardrails = guardrails or []
        self.equity_curve = []

    def _compute_allocations(self, signals: Dict[str, int], date: pd.Timestamp) -> Dict[str, int]:
        """
        Determines share allocations based on buy/sell/hold signals and available cash.
        """
        allocations = {}
        buy_signals = [ticker for ticker, sig in signals.items() if sig == 1]
        if not buy_signals:
            return allocations

        cash_per_asset = self.portfolio.get_cash() / len(buy_signals)

        for ticker, signal in signals.items():
            price = self.market_data.get_price(ticker=ticker, date=date)
            if price is None or price <= 0:
                continue

            if signal == 1:  # Buy
                shares = int(cash_per_asset // price)
                if shares > 0:
                    allocations[ticker] = shares
            elif signal == -1:  # Sell
                allocations[ticker] = -1

        return allocations

    def execute_trades(self, date):
        """
        Executes trades for the portfolio on the specified date using the strategy and market data.

        Args:
            date: The trading date.
        """
        # Generate signal and allocations using portfolio strategy
        signal_data = self.portfolio.strategy.generate_signals(self.market_data, current_date=date)
        day_data = {
            ticker: self.market_data.get_series(ticker).loc[[date]]
            for ticker in self.portfolio.tickers
        }

        allocations = self._compute_allocations(signal_data, date)

        # Apply guardrails
        guardrail_exits = self._evaluate_guardrails(date)
        self._apply_guardrail_exits(guardrail_exits, allocations)

        # Execute all trades
        for ticker, shares in allocations.items():
            price = self.market_data.get_price(ticker=ticker, date=date)
            if price is None or price <= 0:
                continue
            self._execute_single_trade(date, ticker, shares, price, guardrail_exits)

    def _evaluate_guardrails(self, date):
        """
        Evaluates all guardrails for exit signals on the given date.

        Args:
            date: The trading date.

        Returns:
            dict: Tickers signaled for exit by guardrails.
        """
        exits = {}
        for guardrail in self.guardrails:
            exit_signals = guardrail.evaluate(
                self.portfolio.positions,
                {
                    ticker: self.market_data.get_price(ticker=ticker, date=date)
                    for ticker in self.portfolio.positions if ticker != 'CASH'
                }
            )
            exits.update(exit_signals)
        return exits

    def _apply_guardrail_exits(self, exits, allocations):
        """
        Adjusts allocations to force exits as signaled by guardrails.

        Args:
            exits (dict): Tickers to exit.
            allocations (dict): Allocations to be modified in-place.
        """
        for ticker in exits:
            allocations[ticker] = -1
            for guardrail in self.guardrails:
                if hasattr(guardrail, "unregister"):
                    guardrail.unregister(ticker)

    def _execute_single_trade(self, date, ticker, shares, price, exits):
        """
        Executes a buy or sell trade based on share quantity.

        Args:
            date: The trading date.
            ticker (str): The ticker symbol.
            shares (int): Number of shares to buy (>0) or sell (<0).
            price (float): The price per share.
            exits (dict): Guardrail exit signals.
        """
        if shares > 0:
            self._handle_buy_trade(date, ticker, shares, price)
        elif shares < 0:
            self._handle_sell_trade(date, ticker, shares, price, exits)

    def _handle_buy_trade(self, date, ticker, shares, price):
        """
        Handles execution of a buy trade.
        """
        self.portfolio.execute_trade(date, ticker, 'BUY', shares, price, note="Strategy Signal")

    def _handle_sell_trade(self, date, ticker, shares, price, exits):
        """
        Handles execution of a sell trade.
        """
        held = self.portfolio.get_position(ticker)
        if held > 0:
            sell_qty = held if shares == -1 else min(held, abs(shares))
            self.portfolio.execute_trade(
                date, ticker, 'SELL', sell_qty, price,
                note="Trailing Stop Triggered" if ticker in exits else "Strategy Signal"
            )

    def update_equity(self, date):
        """
        Updates and records the portfolio's net worth for the given date.

        Args:
            date: The trading date.

        Returns:
            float: The total portfolio value (net worth).
        """
        total_value = self.portfolio.get_cash()
        for ticker in self.portfolio.positions:
            if ticker == 'CASH':
                continue
            shares = self.portfolio.get_position(ticker)
            price = self.market_data.get_price(ticker=ticker, date=date) or 0.0
            total_value += shares * price
        self.equity_curve.append({'date': date, 'net_worth': total_value})
        return total_value

    def get_equity_curve(self) -> pd.DataFrame:
        """
        Returns the recorded equity curve as a pandas DataFrame.

        Returns:
            pd.DataFrame: DataFrame indexed by date with net worth.
        """
        return pd.DataFrame(self.equity_curve).set_index('date')

    def get_trade_log(self) -> pd.DataFrame:
        """
        Returns the portfolio's trade log as a pandas DataFrame.

        Returns:
            pd.DataFrame: DataFrame containing the trade log.
        """
        return self.portfolio.get_trade_log()
