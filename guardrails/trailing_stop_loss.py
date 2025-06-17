from typing import Dict

from contracts.asset import Asset
from guardrails.base import GuardrailBase,GuardrailFactory


@GuardrailFactory.register("trailing_stop_loss")
class TrailingStopLossGuardrail(GuardrailBase):
    def __init__(self, stop_pct: float = 0.05):
        self.stop_pct = stop_pct
        self.entry_prices = {}
        # self.highest_since_entry = {}

    def register_entry(self, ticker: str, price: float):
        entry_price = self.entry_prices.get(ticker, -1)
        # if price > entry_price:
        #     self.entry_prices[ticker] = price

    def unregister(self, ticker: str):
        self.entry_prices.pop(ticker, None)
        # self.highest_since_entry.pop(ticker, None)

    def evaluate(self, positions: Dict[str, Asset], prices: Dict[str, float]) -> Dict[str, bool]:
        exits = None
        for ticker, asset in positions.items():
            # if ticker == 'CASH':
            #     continue
            if asset.shares <= 0 or ticker not in self.entry_prices:
                continue

            exits = {}
            current_price = prices.get(ticker, 0)

            if ticker not in self.entry_prices:
                self.register_entry(ticker, current_price)
            peak = self.entry_prices.get(ticker)
            if current_price > peak:
                self.entry_prices[ticker] = current_price
            elif current_price < peak * (1 - self.stop_pct):
                print(f"🔻 GuardrailBase: {ticker} triggered trailing stop at {current_price:.2f} (peak: {peak:.2f})")
                exits[ticker] = True

        return exits
