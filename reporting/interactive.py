import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots


def write_equity_explorer(res, prices: pd.DataFrame, strat_name: str, bench_name: str, path: str,
                          caveat: str | None = None,
                          stop_levels: pd.DataFrame | None = None) -> str:
    """Write an interactive HTML chart for exploring a backtest.

    Top panel: strategy equity vs benchmark, the underlying tickers (rebased, faint),
    buy/sell markers, and — when a stop-loss ran — the **active stop level** per held name
    (dashed red), so the intended exit level is visible right next to the actual exit.
    Bottom panel: strategy drawdown. Hover is unified per day (equity, benchmark, and the
    portfolio split); range-selector buttons zoom to 1m/3m/6m/YTD/1y/all.

    Args:
        res: the ``bt`` result.
        prices: the underlying price panel (dates x tickers).
        strat_name: backtest name of the strategy.
        bench_name: backtest name of the benchmark.
        path: output ``.html`` path.
        caveat: a bias stamp rendered under the title, so the chart confesses its caveats.
        stop_levels: dates × tickers of the active stop level (NaN when not holding), in
            price space — rebased here with the same factor as the underlying prices.

    Returns:
        ``path``.
    """
    backtest = res.backtests[strat_name]
    equity = res.prices
    index = equity.index

    strat_equity = equity[strat_name]
    weights = backtest.security_weights.reindex(index).fillna(0.0)
    cash = (1.0 - weights.sum(axis=1)).clip(lower=0.0)
    drawdown = strat_equity / strat_equity.cummax() - 1.0

    fig = make_subplots(rows=2, cols=1, shared_xaxes=True,
                        row_heights=[0.75, 0.25], vertical_spacing=0.04)

    rebased = prices.reindex(index).ffill()
    base = rebased.iloc[0]
    _add_underlying(fig, rebased.div(base) * 100.0)
    if stop_levels is not None:
        _add_stop_levels(fig, stop_levels.reindex(index), base)

    fig.add_trace(go.Scatter(
        x=index, y=equity[bench_name], name=bench_name,
        line=dict(width=1.5, color="gray"),
        hovertemplate="%{y:.1f}<extra>" + bench_name + "</extra>",
    ), row=1, col=1)
    fig.add_trace(go.Scatter(
        x=index, y=strat_equity, name=strat_name,
        line=dict(width=2.5, color="royalblue"),
        customdata=[_split_text(weights.loc[d], cash.loc[d]) for d in index],
        hovertemplate="NAV %{y:.1f}<br>%{customdata}<extra>" + strat_name + "</extra>",
    ), row=1, col=1)
    _add_trade_markers(fig, backtest.positions.reindex(index).fillna(0.0), strat_equity)

    fig.add_trace(go.Scatter(
        x=index, y=drawdown, name="drawdown", showlegend=False,
        line=dict(width=1, color="firebrick"), fill="tozeroy",
        fillcolor="rgba(178,34,34,0.25)",
        hovertemplate="%{y:.1%}<extra>drawdown</extra>",
    ), row=2, col=1)

    title = f"{strat_name}: equity, holdings & trades"
    if caveat:
        title += f"<br><sub>⚠ {caveat}</sub>"
    fig.update_layout(
        title=title,
        template="plotly_white",
        hovermode="x unified",
        legend=dict(orientation="h", yanchor="bottom", y=1.02),
        margin=dict(t=90),
    )
    fig.update_xaxes(
        showspikes=True, spikemode="across", spikethickness=1,
        rangeselector=dict(buttons=[
            dict(count=1, label="1m", step="month", stepmode="backward"),
            dict(count=3, label="3m", step="month", stepmode="backward"),
            dict(count=6, label="6m", step="month", stepmode="backward"),
            dict(label="YTD", step="year", stepmode="todate"),
            dict(count=1, label="1y", step="year", stepmode="backward"),
            dict(step="all"),
        ]),
        row=1, col=1,
    )
    fig.update_yaxes(title_text="Growth of 100", row=1, col=1)
    fig.update_yaxes(title_text="Drawdown", tickformat=".0%", row=2, col=1)
    fig.write_html(path, include_plotlyjs="cdn")
    return path


def _add_underlying(fig: go.Figure, rebased: pd.DataFrame) -> None:
    for ticker in rebased.columns:
        fig.add_trace(go.Scatter(
            x=rebased.index, y=rebased[ticker], name=ticker,
            line=dict(width=1, dash="dot"), opacity=0.4, hoverinfo="skip",
        ), row=1, col=1)


def _add_stop_levels(fig: go.Figure, levels: pd.DataFrame, base: pd.Series) -> None:
    """Dashed red stop-level lines, rebased with the same factor as the underlying prices."""
    for ticker in levels.columns:
        series = levels[ticker]
        if series.isna().all() or ticker not in base.index or not base[ticker] > 0:
            continue
        rebased = series / base[ticker] * 100.0
        fig.add_trace(go.Scatter(
            x=levels.index, y=rebased, name=f"{ticker} stop",
            line=dict(width=1.2, dash="dash", color="crimson"), opacity=0.8,
            connectgaps=False,
            hovertemplate="stop %{y:.1f}<extra>" + ticker + "</extra>",
        ), row=1, col=1)


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
            # Each marker's text carries its own date: unified hover folds nearby days into
            # one box, which otherwise fakes a same-day round trip out of adjacent trades.
            customdata=[_trade_text(d, delta.loc[d], sign) for d in days],
            hovertemplate=f"<b>{label.upper()}</b> %{{customdata}}<extra></extra>",
        ), row=1, col=1)


def _split_text(weights_row: pd.Series, cash: float) -> str:
    parts = [f"{t} {w * 100:.0f}%" for t, w in weights_row.items() if w > 1e-4]
    if cash > 1e-4:
        parts.append(f"cash {cash * 100:.0f}%")
    return " · ".join(parts) if parts else "all cash"


def _trade_text(day: pd.Timestamp, delta_row: pd.Series, sign: int) -> str:
    trades = "<br>".join(
        f"{t} {'+' if d > 0 else ''}{d:.0f} sh"
        for t, d in delta_row.items()
        if abs(d) > 1e-9 and (d > 0) == (sign > 0)
    )
    return f"{day:%b %d, %Y}<br>{trades}"
