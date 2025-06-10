from abc import ABC
from typing import Type, Optional


class AssetBase(ABC):
    """
    Base class for all assets in a portfolio.
    This class is not intended to be instantiated directly.
    """
    # Class property to define the expected quantity type
    asset_type: Optional[Type] = None

    def __init__(self, ticker: str, shares: int | float = 0):
        assert isinstance(ticker, str), "Ticker must be a string"
        self._ticker = ticker.strip().strip('^').upper()

        assert isinstance(shares, self.asset_type), f"Shares must be an {self.asset_type.__name__}"
        self._shares = shares
        self._trade_history: Optional[list] = None  # List to store trade history

    def __repr__(self):
        return f"{self.__class__.__name__}(ticker={self._ticker}, shares={self.shares})"

    def buy(self, quantity: int | float):
        """
        Buy a specified quantity of the asset.
        :param quantity: Number of shares to buy.
        """
        # Type check based on the class's asset_type
        if not isinstance(quantity, self.asset_type):
            raise TypeError(f"Quantity must be of type {self.asset_type.__name__}")

        if quantity <= 0:
            raise ValueError("Cannot buy a negative quantity")
        self._shares += quantity

    def sell(self, quantity: int | float):
        """
        Sell a specified quantity of the asset.
        (Short selling is not allowed in this base class)
        :param quantity: Number of shares to sell.
        """
        # Type check based on the class's asset_type
        if not isinstance(quantity, self.asset_type):
            raise TypeError(f"Quantity must be of type {self.asset_type.__name__}")

        if quantity > self._shares:
            raise ValueError("Cannot sell more than held quantity")
        self._shares -= quantity

    @property
    def shares(self):
        return self._shares

    def is_empty(self):
        return self.shares == 0


class Asset(AssetBase):
    """
    Represents a tradable asset with a ticker and quantity held.
    Fractional Shares are not allowed yet.
    """

    def __init__(self, ticker: str, shares: int = 0):
        self.asset_type = int
        super().__init__(ticker, shares)


class CashAsset(AssetBase):
    """
    Represents the cash reserve in a portfolio.
    """
    # Explicitly override the asset_type to enforce float quantities

    def __init__(self, initial_cash: float = 0.0):
        self.asset_type = float
        super().__init__(ticker='CASH', shares=initial_cash)

    def deposit_cash(self, amount: float):
        try:
            super().buy(amount)
        except ValueError:
            raise ValueError("Cannot deposit a negative amount or more than available cash")

    def withdraw_cash(self, amount: float):
        try:
            super().sell(amount)
        except ValueError:
            raise ValueError("Cannot withdraw more than available cash")
