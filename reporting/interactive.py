import numpy as np
import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots

# A small, modern palette — one strong accent, muted everything else.
_STRAT = "#2563eb"   # strategy line (blue)
_BENCH = "#9ca3af"   # benchmark (gray)
_GAIN = "#16a34a"    # buy markers
_LOSS = "#dc2626"    # sell markers / drawdown
_STOP = "#e11d48"    # stop level (crimson)
_GRID = "rgba(17,24,39,0.06)"
_FONT = "system-ui, -apple-system, 'Segoe UI', Roboto, sans-serif"


def write_equity_explorer(res, prices: pd.DataFrame, strat_name: str, bench_name: str, path: str,
                          caveat: str | None = None,
                          stop_levels: pd.DataFrame | None = None) -> str:
    """Write an interactive HTML explorer for a backtest.

    Everything is framed as **cumulative return %** from the start (0% = breakeven), so
    gains and losses read directly rather than as an abstract NAV. The strategy and
    benchmark are measured from day 0; each underlying ticker from its own first bar. On
    hover, the lines are normalized but the **actual dollar price** is shown — so a trade
    marker reveals the price the fill happened at, which is what you need to investigate a
    move. When a stop-loss ran, its **active stop level** is drawn (dashed crimson) beside
    the name it guards. A second panel shows the strategy's drawdown.

    Controls: a range **slider** to drag any custom window, plus **1M/3M/6M/YTD/1Y/All**
    buttons. Hover is unified per day.

    Args:
        res: the ``bt`` result.
        prices: the underlying price panel (dates × tickers), actual prices.
        strat_name: backtest name of the strategy.
        bench_name: backtest name of the benchmark.
        path: output ``.html`` path.
        caveat: a bias stamp rendered under the title.
        stop_levels: dates × tickers of the active stop level (NaN when flat), price space.

    Returns:
        ``path``.
    """
    backtest = res.backtests[strat_name]
    equity = res.prices
    index = equity.index

    strat_ret = _pct(equity[strat_name])
    bench_ret = _pct(equity[bench_name])
    weights = backtest.security_weights.reindex(index).fillna(0.0)
    cash = (1.0 - weights.sum(axis=1)).clip(lower=0.0)
    drawdown = (equity[strat_name] / equity[strat_name].cummax() - 1.0) * 100.0

    prices = prices.reindex(index).ffill()
    base = prices.apply(_first_valid)  # per-ticker normalization base (own first bar)

    fig = make_subplots(rows=2, cols=1, shared_xaxes=True,
                        row_heights=[0.74, 0.26], vertical_spacing=0.06)

    _add_underlying(fig, prices, base)
    if stop_levels is not None:
        _add_stop_levels(fig, stop_levels.reindex(index), base)
    fig.add_hline(y=0.0, line=dict(width=1, dash="dot", color="rgba(17,24,39,0.25)"), row=1, col=1)

    fig.add_trace(go.Scatter(
        x=index, y=bench_ret, name=bench_name, mode="lines",
        line=dict(width=1.6, color=_BENCH),
        hovertemplate="%{y:+.2f}%<extra>" + bench_name + "</extra>",
    ), row=1, col=1)
    fig.add_trace(go.Scatter(
        x=index, y=strat_ret, name=strat_name, mode="lines",
        line=dict(width=2.6, color=_STRAT),
        customdata=[_split_text(weights.loc[d], cash.loc[d]) for d in index],
        hovertemplate="<b>%{y:+.2f}%</b><br>%{customdata}<extra>" + strat_name + "</extra>",
    ), row=1, col=1)
    _add_trade_markers(fig, backtest.positions.reindex(index).fillna(0.0), prices, strat_ret)

    fig.add_trace(go.Scatter(
        x=index, y=drawdown, name="drawdown", showlegend=False,
        line=dict(width=1, color=_LOSS), fill="tozeroy",
        fillcolor="rgba(220,38,38,0.16)",
        hovertemplate="%{y:.2f}%<extra>drawdown</extra>",
    ), row=2, col=1)

    _style(fig, strat_name, bench_name, caveat)
    fig.write_html(
        path, include_plotlyjs="cdn",
        config=dict(displaylogo=False, scrollZoom=True, responsive=True,
                    modeBarButtonsToRemove=["lasso2d", "select2d", "autoScale2d"],
                    toImageButtonOptions=dict(filename=f"{strat_name}_explorer", scale=2)),
    )
    return path


def _pct(series: pd.Series) -> pd.Series:
    """Cumulative % return from the first value (0% = breakeven)."""
    return (series / series.iloc[0] - 1.0) * 100.0


def _first_valid(series: pd.Series) -> float:
    idx = series.first_valid_index()
    return series.loc[idx] if idx is not None else np.nan


def _add_underlying(fig: go.Figure, prices: pd.DataFrame, base: pd.Series) -> None:
    """Faint dotted % lines for each held name; hover reveals the real dollar price."""
    for ticker in prices.columns:
        b = base.get(ticker, np.nan)
        if not (pd.notna(b) and b > 0):
            continue
        fig.add_trace(go.Scatter(
            x=prices.index, y=(prices[ticker] / b - 1.0) * 100.0, name=ticker, mode="lines",
            line=dict(width=1, dash="dot"), opacity=0.35, legendgroup="underlying",
            customdata=prices[ticker],
            hovertemplate="%{customdata:$,.2f}<extra>" + ticker + "</extra>",
        ), row=1, col=1)


def _add_stop_levels(fig: go.Figure, levels: pd.DataFrame, base: pd.Series) -> None:
    """Dashed stop-level lines in the same % space as the underlying; hover shows the price."""
    for ticker in levels.columns:
        series = levels[ticker]
        b = base.get(ticker, np.nan)
        if series.isna().all() or not (pd.notna(b) and b > 0):
            continue
        fig.add_trace(go.Scatter(
            x=levels.index, y=(series / b - 1.0) * 100.0, name=f"{ticker} stop", mode="lines",
            line=dict(width=1.3, dash="dash", color=_STOP), opacity=0.85,
            connectgaps=False, legendgroup="stops", customdata=series,
            hovertemplate="stop %{customdata:$,.2f}<extra>" + ticker + "</extra>",
        ), row=1, col=1)


def _add_trade_markers(fig: go.Figure, positions: pd.DataFrame, prices: pd.DataFrame,
                       strat_ret: pd.Series) -> None:
    delta = positions.diff().fillna(positions)
    for label, mask, symbol, color, sign in (
        ("buy", delta.gt(0).any(axis=1), "triangle-up", _GAIN, 1),
        ("sell", delta.lt(0).any(axis=1), "triangle-down", _LOSS, -1),
    ):
        days = delta.index[mask]
        if len(days) == 0:
            continue
        fig.add_trace(go.Scatter(
            x=days, y=strat_ret.reindex(days), name=label, mode="markers",
            marker=dict(symbol=symbol, color=color, size=10, line=dict(width=1, color="white")),
            # Each marker carries its own date + fill price: unified hover folds nearby days
            # into one box, which otherwise fakes a same-day round trip out of adjacent trades.
            customdata=[_trade_text(d, delta.loc[d], prices.loc[d], sign) for d in days],
            hovertemplate="%{customdata}<extra></extra>",
        ), row=1, col=1)


def _split_text(weights_row: pd.Series, cash: float) -> str:
    parts = [f"{t} {w * 100:.0f}%" for t, w in weights_row.items() if w > 1e-4]
    if cash > 1e-4:
        parts.append(f"cash {cash * 100:.0f}%")
    return " · ".join(parts) if parts else "all cash"


def _trade_text(day: pd.Timestamp, delta_row: pd.Series, price_row: pd.Series, sign: int) -> str:
    lines = []
    for t, d in delta_row.items():
        if abs(d) <= 1e-9 or (d > 0) != (sign > 0):
            continue
        px = price_row.get(t, float("nan"))
        at = f" @ ${px:,.2f}" if pd.notna(px) else ""
        lines.append(f"{t} {'+' if d > 0 else '−'}{abs(d):.0f} sh{at}")
    head = "BUY" if sign > 0 else "SELL"
    return f"<b>{head}</b> · {day:%b %d, %Y}<br>" + "<br>".join(lines)


def _style(fig: go.Figure, strat_name: str, bench_name: str, caveat: str | None) -> None:
    title = f"{strat_name} — cumulative return vs {bench_name}"
    if caveat:
        title += f"<br><sub style='color:#b45309'>⚠ {caveat}</sub>"
    fig.update_layout(
        title=dict(text=title, x=0.015, xanchor="left", font=dict(size=20)),
        template="plotly_white",
        font=dict(family=_FONT, size=13, color="#111827"),
        hovermode="x unified",
        hoverlabel=dict(bgcolor="white", bordercolor="rgba(17,24,39,0.12)", font_size=12),
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
        margin=dict(t=110, l=60, r=24, b=24),
        plot_bgcolor="white", paper_bgcolor="white",
    )
    fig.update_xaxes(showgrid=True, gridcolor=_GRID, showspikes=True, spikemode="across",
                     spikethickness=1, spikecolor="rgba(17,24,39,0.3)", spikedash="dot")
    fig.update_xaxes(
        rangeselector=dict(
            x=0, y=1.06, xanchor="left",
            bgcolor="rgba(17,24,39,0.04)", activecolor=_STRAT, font=dict(color="#374151"),
            buttons=[
                dict(count=1, label="1M", step="month", stepmode="backward"),
                dict(count=3, label="3M", step="month", stepmode="backward"),
                dict(count=6, label="6M", step="month", stepmode="backward"),
                dict(label="YTD", step="year", stepmode="todate"),
                dict(count=1, label="1Y", step="year", stepmode="backward"),
                dict(step="all", label="All"),
            ]),
        row=1, col=1)
    fig.update_xaxes(rangeslider=dict(visible=True, thickness=0.07,
                                      bgcolor="rgba(17,24,39,0.02)"), row=2, col=1)
    fig.update_yaxes(title_text="Return", ticksuffix="%", showgrid=True, gridcolor=_GRID,
                     zeroline=False, row=1, col=1)
    fig.update_yaxes(title_text="Drawdown", ticksuffix="%", showgrid=True, gridcolor=_GRID,
                     row=2, col=1)
