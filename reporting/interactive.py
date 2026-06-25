import numpy as np
import pandas as pd
import plotly.graph_objects as go


def write_equity_explorer(res, prices: pd.DataFrame, strat_name: str, bench_name: str, path: str) -> str:
    """Write an interactive HTML chart for exploring a backtest.

    Shows the strategy equity curve and benchmark, the underlying tickers (rebased, faint),
    and buy/sell markers where positions change. Hovering the equity curve reveals the
    portfolio split (each holding's weight + cash) on that day — the point is to *see* what
    the strategy was doing and when.

    Args:
        res: the ``bt`` result.
        prices: the underlying price panel (dates x tickers).
        strat_name: backtest name of the strategy.
        bench_name: backtest name of the benchmark.
        path: output ``.html`` path.

    Returns:
        ``path``.
    """
    backtest = res.backtests[strat_name]
    equity = res.prices
    index = equity.index

    strat_equity = equity[strat_name]
    weights = backtest.security_weights.reindex(index).fillna(0.0)
    cash = (1.0 - weights.sum(axis=1)).clip(lower=0.0)

    fig = go.Figure()
    _add_underlying(fig, prices, index)
    fig.add_trace(go.Scatter(
        x=index, y=equity[bench_name], name=bench_name,
        line=dict(width=1.5, color="gray"),
        hovertemplate="%{y:.1f}<extra>" + bench_name + "</extra>",
    ))
    fig.add_trace(go.Scatter(
        x=index, y=strat_equity, name=strat_name,
        line=dict(width=2.5, color="royalblue"),
        customdata=[_split_text(weights.loc[d], cash.loc[d]) for d in index],
        hovertemplate="NAV %{y:.1f}<br>%{customdata}<extra>" + strat_name + "</extra>",
    ))
    _add_trade_markers(fig, backtest.positions.reindex(index).fillna(0.0), strat_equity)

    fig.update_layout(
        title=f"{strat_name}: equity, holdings & trades",
        template="plotly_white",
        hovermode="closest",
        yaxis_title="Growth of 100",
        legend=dict(orientation="h", yanchor="bottom", y=1.02),
    )
    fig.write_html(path, include_plotlyjs="cdn")
    return path


def _add_underlying(fig: go.Figure, prices: pd.DataFrame, index: pd.Index) -> None:
    rebased = prices.reindex(index).ffill()
    rebased = rebased.div(rebased.iloc[0]) * 100.0
    for ticker in rebased.columns:
        fig.add_trace(go.Scatter(
            x=index, y=rebased[ticker], name=ticker,
            line=dict(width=1, dash="dot"), opacity=0.4, hoverinfo="skip",
        ))


def _add_trade_markers(fig: go.Figure, positions: pd.DataFrame, strat_equity: pd.Series) -> None:
    delta = positions.diff().fillna(positions)
    for label, mask, symbol, color, sign in (
        ("buy", delta.gt(0).any(axis=1), "triangle-up", "green", 1),
        ("sell", delta.lt(0).any(axis=1), "triangle-down", "firebrick", -1),
    ):
        days = delta.index[mask]
        if len(days) == 0:
            continue
        fig.add_trace(go.Scatter(
            x=days, y=strat_equity.reindex(days), name=label, mode="markers",
            marker=dict(symbol=symbol, color=color, size=9),
            customdata=[_trade_text(delta.loc[d], sign) for d in days],
            hovertemplate=f"<b>{label.upper()}</b><br>%{{customdata}}<extra></extra>",
        ))


def _split_text(weights_row: pd.Series, cash: float) -> str:
    parts = [f"{t} {w * 100:.0f}%" for t, w in weights_row.items() if w > 1e-4]
    if cash > 1e-4:
        parts.append(f"cash {cash * 100:.0f}%")
    return " · ".join(parts) if parts else "all cash"


def _trade_text(delta_row: pd.Series, sign: int) -> str:
    return "<br>".join(
        f"{t} {'+' if d > 0 else ''}{d:.0f} sh"
        for t, d in delta_row.items()
        if abs(d) > 1e-9 and (d > 0) == (sign > 0)
    )
