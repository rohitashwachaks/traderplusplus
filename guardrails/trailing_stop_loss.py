from typing import Dict

from contracts.asset import Asset
from guardrails.base import GuardrailBase, GuardrailFactory


@GuardrailFactory.register("trailing_stop_loss")
class TrailingStopLossGuardrail(GuardrailBase):
    def __init__(self, stop_pct: float = 0.5):
        super().__init__()
        self.stop_pct = stop_pct
        self.entry_prices = {}

    def register_entry(self, ticker: str, price: float):
        # Register the entry price if not already present
        if ticker not in self.entry_prices:
            self.entry_prices[ticker] = price

    def unregister(self, ticker: str):
        self.entry_prices.pop(ticker, None)

    def evaluate(self, positions: Dict[str, Asset], prices: Dict[str, float]) -> Dict[str, bool]:
        exits = {}
        for ticker, asset in positions.items():
            if asset.shares <= 0:
                self.unregister(ticker)
                continue

            current_price = prices.get(ticker, 0)

            if ticker not in self.entry_prices:
                self.register_entry(ticker, current_price)
            peak = self.entry_prices.get(ticker)
            if current_price > peak:
                self.entry_prices[ticker] = current_price
            elif current_price < peak * (1 - self.stop_pct):
                print(f"🔻 GuardrailBase: {ticker} triggered trailing stop at {current_price:.2f} (peak: {peak:.2f})")
                exits[ticker] = True
                self.unregister(ticker)

        return exits
