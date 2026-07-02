import logging
from dataclasses import dataclass

import pandas as pd

from brokers.base import Broker

log = logging.getLogger("traderplusplus")


@dataclass
class Order:
    """One whole-share market order in a rebalance plan."""
    ticker: str
    side: str          # "buy" or "sell"
    qty: int
    target_weight: float
    current_shares: float
    target_shares: int


def build_plan(
    target_weights: pd.Series,
    prices: pd.Series,
    positions: dict[str, float],
    equity: float,
) -> list[Order]:
    """Diff current holdings against target weights into whole-share market orders.

    Target shares = floor(weight * equity / price). Any ticker held but no longer in the
    target is fully closed. Sub-share deltas are dropped (we trade whole shares). Sells are
    ordered before buys so closing trades free up cash for the opening ones.

    Args:
        target_weights: desired weight per ticker (need not sum to 1; remainder is cash).
        prices: latest price per ticker.
        positions: current holdings ``{ticker: shares}``.
        equity: total account value to size against.

    Returns:
        Orders to submit, sells first.
    """
    tickers = sorted(set(target_weights.index) | set(positions))
    orders: list[Order] = []
    for ticker in tickers:
        weight = float(target_weights.get(ticker, 0.0))
        price = float(prices.get(ticker, float("nan")))
        current = float(positions.get(ticker, 0.0))

        if price > 0 and weight > 0:
            target_shares = int(weight * equity // price)
        else:
            target_shares = 0  # no price or zero target → hold nothing

        delta = target_shares - round(current)
        if abs(delta) < 1:
            continue
        orders.append(Order(
            ticker=ticker,
            side="buy" if delta > 0 else "sell",
            qty=abs(int(delta)),
            target_weight=weight,
            current_shares=current,
            target_shares=target_shares,
        ))
    orders.sort(key=lambda o: o.side != "sell")
    return orders


def format_plan(orders: list[Order], equity: float) -> str:
    """Human-readable preview table of a rebalance plan."""
    if not orders:
        return f"Account equity ${equity:,.2f} — already at target, no orders."
    lines = [f"Account equity ${equity:,.2f} — {len(orders)} order(s):",
             f"  {'TICKER':<8}{'SIDE':<6}{'QTY':>6}  {'CUR→TGT shares':>16}  {'TGT wt':>7}"]
    for o in orders:
        lines.append(f"  {o.ticker:<8}{o.side:<6}{o.qty:>6}  "
                     f"{o.current_shares:>7.0f} → {o.target_shares:<6}  {o.target_weight:>6.1%}")
    return "\n".join(lines)


def execute_plan(broker: Broker, orders: list[Order]) -> None:
    """Submit every order in the plan to the broker."""
    log.warning("Submitting %d order(s) to the (paper) broker", len(orders))
    for o in orders:
        broker.submit(o.ticker, o.qty, o.side)
        log.info("  submitted %s %d %s", o.side, o.qty, o.ticker)
