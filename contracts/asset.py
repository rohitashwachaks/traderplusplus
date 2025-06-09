from abc import ABC


class AssetBase(ABC):
    """
    Base class for all assets in a portfolio.
    This class is not intended to be instantiated directly.
    """
    def __init__(self, ticker: str, shares: int | float = 0):
        self.ticker = ticker
        self._shares = shares
        self.trade_history = []

    def __repr__(self):
        return f"{self.__class__.__name__}(ticker={self.ticker}, shares={self.shares})"

    def buy(self, quantity: int | float):
        """
        Buy a specified quantity of the asset.
        :param quantity: Number of shares to buy.
        """
        if quantity < 0:
            raise ValueError("Cannot buy a negative quantity")
        self._shares += quantity

    def sell(self, quantity: int | float):
        """
        Sell a specified quantity of the asset.
        (Short selling is not allowed in this base class)
        :param quantity: Number of shares to sell.
        """
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
    """
    def __init__(self, ticker: str, shares: int = 0):
        super().__init__(ticker, shares)


class CashAsset(AssetBase):
    """
    Represents the cash reserve in a portfolio.
    """
    def __init__(self, initial_cash: float = 0.0):
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
