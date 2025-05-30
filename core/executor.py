import pandas as pd
from typing import Dict, List

from core.guardrails.base import Guardrail


class PortfolioExecutor:
    def __init__(self, starting_cash: float = 100000.0, guardrails: List[Guardrail] = None):
        self.cash = starting_cash
        self.positions: Dict[str, int] = {}  # {symbol: number of shares}
        self.trade_log = []
        self.equity_curve = []
        self.position_history: Dict[str, List[int]] = {}
        self.guardrails = guardrails or []
        print(f"Initialized PortfolioExecutor with starting cash: {self.cash}")

    from typing import Dict

    def execute_trades(self, date, allocations: Dict[str, int], prices: Dict[str, float]):
        guardrail_exits = {}

        # 1. Evaluate guardrails
        for guardrail in self.guardrails:
            exit_signals = guardrail.evaluate(self.positions, prices)
            guardrail_exits.update(exit_signals)

        # 2. Inject forced liquidations
        for symbol in guardrail_exits:
            allocations[symbol] = -1
            for guardrail in self.guardrails:
                if hasattr(guardrail, "unregister"):
                    guardrail.unregister(symbol)

        # 3. Execute trades
        for symbol, shares in allocations.items():
            price = prices.get(symbol)
            if price is None or price <= 0:
                continue

            # --- BUY ---
            if shares > 0:
                cost = shares * price
                if self.cash >= cost:
                    self.cash -= cost
                    self.positions[symbol] = self.positions.get(symbol, 0) + shares
                    self.trade_log.append({
                        'date': date,
                        'symbol': symbol,
                        'action': 'BUY',
                        'shares': shares,
                        'price': price,
                        'cost': cost,
                        'cash_remaining': self.cash,
                        'note': 'Strategy Signal'
                    })

                    # Register with guardrails
                    for guardrail in self.guardrails:
                        if hasattr(guardrail, "register_entry"):
                            guardrail.register_entry(symbol, price)

            # --- SELL ---
            elif shares < 0:
                held = self.positions.get(symbol, 0)
                if held > 0:
                    sell_qty = held if shares == -1 else min(held, abs(shares))
                    revenue = sell_qty * price
                    self.cash += revenue
                    self.positions[symbol] -= sell_qty
                    if self.positions[symbol] == 0:
                        del self.positions[symbol]

                    note = "Trailing Stop Triggered" if symbol in guardrail_exits else "Strategy Signal"
                    self.trade_log.append({
                        'date': date,
                        'symbol': symbol,
                        'action': 'SELL',
                        'shares': sell_qty,
                        'price': price,
                        'revenue': revenue,
                        'cash_remaining': self.cash,
                        'note': note
                    })

    def update_equity(self, date, prices: Dict[str, float]):
        position_value = 0.0

        for symbol in self.positions:
            shares = self.positions[symbol]
            price = prices.get(symbol, 0.0)
            value = shares * price
            position_value += value

            # 👇 Record share count for this asset
            if symbol not in self.position_history:
                self.position_history[symbol] = []
            self.position_history[symbol].append(shares)

        total_equity = position_value + self.cash
        self.equity_curve.append({'date': date, 'net_worth': total_equity})
        return total_equity

    def get_trade_log(self) -> pd.DataFrame:
        return pd.DataFrame(self.trade_log)

    def get_equity_curve(self) -> pd.DataFrame:
        return pd.DataFrame(self.equity_curve).set_index('date')
