from typing import Dict
from core.guardrails.base import Guardrail


class TrailingStopLossGuardrail(Guardrail):
    def __init__(self, stop_pct: float = 0.05):
        self.stop_pct = stop_pct
        self.entry_prices = {}
        self.highest_since_entry = {}

    def register_entry(self, symbol: str, price: float):
        self.entry_prices[symbol] = price
        self.highest_since_entry[symbol] = price

    def unregister(self, symbol: str):
        self.entry_prices.pop(symbol, None)
        self.highest_since_entry.pop(symbol, None)

    def evaluate(self, positions: Dict[str, int], prices: Dict[str, float]) -> Dict[str, bool]:
        exits = {}
        for symbol, shares in positions.items():
            if shares <= 0 or symbol not in self.entry_prices:
                continue

            current_price = prices.get(symbol, 0)
            peak = self.highest_since_entry.get(symbol, self.entry_prices[symbol])
            if current_price > peak:
                self.highest_since_entry[symbol] = current_price
            elif current_price < peak * (1 - self.stop_pct):
                print(f"🔻 Guardrail: {symbol} triggered trailing stop at {current_price:.2f} (peak: {peak:.2f})")
                exits[symbol] = True

        return exits
