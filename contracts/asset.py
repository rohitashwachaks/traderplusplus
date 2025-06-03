class Asset:
    """
    Represents a tradable asset with a ticker and quantity held.
    """
    def __init__(self, ticker: str, shares: int = 0):
        self.ticker = ticker
        self.shares = shares
        self.trade_history = []

    @property
    def balance(self):
        return self.shares

    def buy(self, quantity: int):
        self.shares += quantity

    def sell(self, quantity: int):
        if quantity > self.shares:
            raise ValueError("Cannot sell more than held quantity")
        self.shares -= quantity

    def is_empty(self):
        return self.shares == 0


class CashAsset(Asset):
    """
    Represents the cash reserve in a portfolio.
    """
    def __init__(self, initial_cash: float = 0.0):
        super().__init__(ticker='CASH', shares=initial_cash)

    @property
    def balance(self):
        return self.shares

    def deposit_cash(self, amount: float):
        if amount < 0:
            raise ValueError("Cannot add negative cash")
        self.shares += amount

    def withdraw_cash(self, amount: float):
        if amount > self.shares:
            raise ValueError("Cannot withdraw more than available cash")
        self.shares -= amount
