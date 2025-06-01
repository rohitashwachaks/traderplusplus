from typing import Dict

from contracts.asset import Asset
from core.guardrails.base import Guardrail


class TrailingStopLossGuardrail(Guardrail):
    def __init__(self, stop_pct: float = 0.05):
        self.stop_pct = stop_pct
        self.entry_prices = {}
        self.highest_since_entry = {}

    def register_entry(self, ticker: str, price: float):
        self.entry_prices[ticker] = price
        self.highest_since_entry[ticker] = price

    def unregister(self, ticker: str):
        self.entry_prices.pop(ticker, None)
        self.highest_since_entry.pop(ticker, None)

    def evaluate(self, positions: Dict[str, Asset], prices: Dict[str, float]) -> Dict[str, bool]:
        exits = {}
        for ticker, asset in positions.items():
            if ticker == 'CASH':
                continue
            if asset.shares <= 0 or ticker not in self.entry_prices:
                continue

            current_price = prices.get(ticker, 0)
            peak = self.highest_since_entry.get(ticker, self.entry_prices[ticker])
            if current_price > peak:
                self.highest_since_entry[ticker] = current_price
            elif current_price < peak * (1 - self.stop_pct):
                print(f"🔻 Guardrail: {ticker} triggered trailing stop at {current_price:.2f} (peak: {peak:.2f})")
                exits[ticker] = True

        return exits
