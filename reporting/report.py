import logging
import os

import matplotlib

matplotlib.use("Agg")  # headless: write figures to disk, never open a window
import matplotlib.pyplot as plt
import pandas as pd
import quantstats

from reporting.interactive import write_equity_explorer

log = logging.getLogger("traderplusplus")


def write_reports(res, out_dir: str, strat_name: str, bench_name: str, prices: pd.DataFrame,
                  caveats: list[str] | None = None,
                  stop_levels: pd.DataFrame | None = None) -> dict[str, str]:
    """Write the full report set for a finished backtest.

    Produces CSVs (equity curve, daily returns, bt stats table, quantstats metrics vs the
    benchmark, daily turnover), PNGs (equity-vs-benchmark, drawdown), a quantstats HTML
    tearsheet, and an interactive HTML explorer (equity + holdings + trades, with per-day
    portfolio split on hover). Every ``caveat`` (bias stamp) is written **into** the
    artifacts — CSV header comments (readable back with ``comment='#'``) and HTML titles —
    so a file separated from its run log still confesses what it can't promise.

    Args:
        res: the ``bt`` result holding the strategy and benchmark.
        out_dir: directory to write artifacts into (created if missing).
        strat_name: backtest name of the strategy.
        bench_name: backtest name of the benchmark.
        prices: the underlying price panel, for the interactive explorer.
        caveats: bias stamps in force for this run.
        stop_levels: active stop level per ticker (from a stop-loss guardrail), overlaid on
            the explorer so the intended exit level is visible against the actual exit.

    Returns:
        Mapping of artifact label to file path.
    """
    os.makedirs(out_dir, exist_ok=True)
    caveats = caveats or []

    equity = res.prices
    returns = equity.pct_change().dropna()
    strat_returns = returns[strat_name]
    bench_returns = returns[bench_name]

    paths = {
        "equity_curve": os.path.join(out_dir, "equity_curve.csv"),
        "daily_returns": os.path.join(out_dir, "daily_returns.csv"),
        "stats": os.path.join(out_dir, "stats.csv"),
        "turnover": os.path.join(out_dir, "turnover.csv"),
        "equity_png": os.path.join(out_dir, "equity_vs_benchmark.png"),
        "drawdown_png": os.path.join(out_dir, "drawdown.png"),
        "explorer": os.path.join(out_dir, "equity_explorer.html"),
    }

    _stamped_csv(equity, paths["equity_curve"], caveats)
    _stamped_csv(returns, paths["daily_returns"], caveats)
    _stamped_csv(res.stats, paths["stats"], caveats)
    _stamped_csv(res.backtests[strat_name].turnover.rename("turnover"), paths["turnover"], caveats)
    _plot_equity(equity, paths["equity_png"])
    _plot_drawdown(equity[strat_name], strat_name, paths["drawdown_png"])
    write_equity_explorer(res, prices, strat_name, bench_name, paths["explorer"],
                          caveat="; ".join(caveats) or None, stop_levels=stop_levels)

    # quantstats' alpha/beta/tearsheet need return variance; a flat (all-cash) curve has
    # none, so skip them explicitly rather than crash on the regression.
    if strat_returns.dropna().nunique() <= 1:
        log.warning("Strategy returns are flat (no variance) — skipping quantstats metrics "
                    "and tearsheet (alpha/beta undefined). Other artifacts still written.")
    else:
        paths["metrics"] = os.path.join(out_dir, "metrics.csv")
        paths["tearsheet"] = os.path.join(out_dir, "tearsheet.html")
        metrics = quantstats.reports.metrics(
            strat_returns, benchmark=bench_returns, mode="full", display=False
        )
        _stamped_csv(metrics, paths["metrics"], caveats)
        title = f"{strat_name} vs {bench_name}"
        if caveats:
            title += " — ⚠ " + "; ".join(caveats)
        quantstats.reports.html(
            strat_returns, benchmark=bench_returns, output=paths["tearsheet"], title=title,
        )
    return paths


def _stamped_csv(frame, path: str, caveats: list[str]) -> None:
    """Write a CSV with each caveat as a leading ``#`` comment line (pandas: ``comment='#'``)."""
    with open(path, "w") as fh:
        for caveat in caveats:
            fh.write(f"# BIAS: {caveat}\n")
        frame.to_csv(fh)


def _plot_equity(equity, path: str) -> None:
    ax = equity.div(equity.iloc[0]).plot(figsize=(11, 5), title="Equity vs Benchmark (rebased)")
    ax.set_ylabel("Growth of 1")
    ax.figure.savefig(path, bbox_inches="tight", dpi=120)
    plt.close(ax.figure)


def _plot_drawdown(equity_series, name: str, path: str) -> None:
    drawdown = equity_series / equity_series.cummax() - 1.0
    ax = drawdown.plot(figsize=(11, 4), title=f"Drawdown — {name}", color="firebrick")
    ax.fill_between(drawdown.index, drawdown.values, 0, color="firebrick", alpha=0.3)
    ax.set_ylabel("Drawdown")
    ax.figure.savefig(path, bbox_inches="tight", dpi=120)
    plt.close(ax.figure)
