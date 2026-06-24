import os

import matplotlib

matplotlib.use("Agg")  # headless: write figures to disk, never open a window
import matplotlib.pyplot as plt
import quantstats


def write_reports(res, out_dir: str, strat_name: str, bench_name: str) -> dict[str, str]:
    """Write the full report set for a finished backtest.

    Produces CSVs (equity curve, daily returns, bt stats table, quantstats metrics vs the
    benchmark), PNGs (equity-vs-benchmark, drawdown), and a quantstats HTML tearsheet
    covering the return distribution, drawdown, rolling Sharpe, and alpha/beta/risk.

    Args:
        res: the ``bt`` result holding the strategy and benchmark.
        out_dir: directory to write artifacts into (created if missing).
        strat_name: backtest name of the strategy.
        bench_name: backtest name of the benchmark.

    Returns:
        Mapping of artifact label to file path.
    """
    os.makedirs(out_dir, exist_ok=True)

    equity = res.prices
    returns = equity.pct_change().dropna()
    strat_returns = returns[strat_name]
    bench_returns = returns[bench_name]

    paths = {
        "equity_curve": os.path.join(out_dir, "equity_curve.csv"),
        "daily_returns": os.path.join(out_dir, "daily_returns.csv"),
        "stats": os.path.join(out_dir, "stats.csv"),
        "metrics": os.path.join(out_dir, "metrics.csv"),
        "equity_png": os.path.join(out_dir, "equity_vs_benchmark.png"),
        "drawdown_png": os.path.join(out_dir, "drawdown.png"),
        "tearsheet": os.path.join(out_dir, "tearsheet.html"),
    }

    equity.to_csv(paths["equity_curve"])
    returns.to_csv(paths["daily_returns"])
    res.stats.to_csv(paths["stats"])
    quantstats.reports.metrics(
        strat_returns, benchmark=bench_returns, mode="full", display=False
    ).to_csv(paths["metrics"])

    _plot_equity(equity, paths["equity_png"])
    _plot_drawdown(equity[strat_name], strat_name, paths["drawdown_png"])

    quantstats.reports.html(
        strat_returns,
        benchmark=bench_returns,
        output=paths["tearsheet"],
        title=f"{strat_name} vs {bench_name}",
    )
    return paths


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
