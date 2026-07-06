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


def reconcile(planned: list[dict], broker_orders: list[dict],
              planned_prices: dict[str, float]) -> pd.DataFrame:
    """Diff a journaled plan against the broker's actual orders and fills.

    One row per (ticker, side): planned vs filled quantity, the plan's reference close vs
    the actual average fill, and the signed slippage in bps (positive = the fill cost money
    versus the price the backtest assumed — buys filled higher, sells filled lower). Broker
    orders the plan doesn't contain come back with status ``unplanned`` — an order the
    journal doesn't know about is a red flag, not a rounding error.

    Args:
        planned: order dicts from the journal (``ticker, side, qty``).
        broker_orders: broker order history (``symbol, side, qty, filled_qty,
            filled_avg_price, status``).
        planned_prices: the close per ticker the plan was sized against.
    """
    fills: dict[tuple[str, str], dict[str, float]] = {}
    for o in broker_orders:
        key = (o["symbol"], o["side"])
        agg = fills.setdefault(key, {"filled_qty": 0.0, "notional": 0.0})
        agg["filled_qty"] += o["filled_qty"]
        agg["notional"] += o["filled_qty"] * o["filled_avg_price"]

    rows = []
    for p in planned:
        key = (p["ticker"], p["side"])
        agg = fills.pop(key, None)
        filled_qty = agg["filled_qty"] if agg else 0.0
        fill_price = (agg["notional"] / agg["filled_qty"]) if agg and agg["filled_qty"] else float("nan")
        ref = float(planned_prices.get(p["ticker"], float("nan")))
        sign = 1.0 if p["side"] == "buy" else -1.0
        slippage = sign * (fill_price / ref - 1.0) * 1e4 if filled_qty and ref > 0 else float("nan")
        status = ("filled" if filled_qty >= p["qty"]
                  else "partial" if filled_qty > 0 else "missing")
        rows.append({"ticker": p["ticker"], "side": p["side"], "planned_qty": p["qty"],
                     "filled_qty": filled_qty, "ref_price": ref, "fill_price": fill_price,
                     "slippage_bps": slippage, "status": status})

    for (symbol, side), agg in fills.items():
        if agg["filled_qty"] == 0:
            continue
        rows.append({"ticker": symbol, "side": side, "planned_qty": 0,
                     "filled_qty": agg["filled_qty"], "ref_price": float("nan"),
                     "fill_price": agg["notional"] / agg["filled_qty"],
                     "slippage_bps": float("nan"), "status": "unplanned"})

    return pd.DataFrame(rows, columns=["ticker", "side", "planned_qty", "filled_qty",
                                       "ref_price", "fill_price", "slippage_bps", "status"])
