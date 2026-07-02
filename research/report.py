"""Reports for a universe sweep — the distribution of single-name outcomes.

The headline artifact is an alpha-vs-beta scatter with marginal histograms: instead of one
ticker's curve, you see how the rule fared across the whole universe and what share of names
actually beat the benchmark. Any universe bias (e.g. survivorship) is stamped on the chart.
"""
import os

import numpy as np
import pandas as pd
import plotly.express as px


def write_distribution_report(
    metrics: pd.DataFrame,
    out_dir: str,
    strat_name: str,
    *,
    caveat: str | None = None,
) -> dict[str, str]:
    """Write per-name metrics, a summary, and an interactive alpha/beta distribution chart.

    Args:
        metrics: per-ticker frame from :func:`research.sweep.sweep_universe`.
        out_dir: directory for artifacts (created if missing).
        strat_name: strategy name, for titles/filenames.
        caveat: a bias stamp (e.g. the universe's survivorship caveat) shown on the chart.

    Returns:
        Mapping of artifact label to file path.
    """
    os.makedirs(out_dir, exist_ok=True)
    paths: dict[str, str] = {}

    per_name = os.path.join(out_dir, "per_name_metrics.csv")
    metrics.to_csv(per_name)
    paths["per_name"] = per_name

    summary = _summary(metrics)
    summary_path = os.path.join(out_dir, "distribution_summary.csv")
    summary.to_csv(summary_path, header=["value"])
    paths["summary"] = summary_path

    chart = os.path.join(out_dir, "alpha_beta_distribution.html")
    _write_chart(metrics, strat_name, caveat, chart)
    paths["distribution"] = chart

    return paths


def _summary(metrics: pd.DataFrame) -> pd.Series:
    return pd.Series({
        "names": float(len(metrics)),
        "median_alpha": metrics["alpha"].median(),
        "mean_alpha": metrics["alpha"].mean(),
        "pct_positive_alpha": (metrics["alpha"] > 0).mean(),
        "median_beta": metrics["beta"].median(),
        "median_sharpe": metrics["sharpe"].median(),
        "pct_beat_benchmark": (metrics["excess_return"] > 0).mean(),
    })


def _write_chart(metrics: pd.DataFrame, strat_name: str, caveat: str | None, path: str) -> None:
    data = metrics.reset_index()
    data["alpha sign"] = np.where(data["alpha"] > 0, "positive α", "negative α")
    title = f"{strat_name}: alpha vs beta across {len(metrics)} names"
    if caveat:
        title += f"<br><sub>⚠ {caveat}</sub>"
    fig = px.scatter(
        data, x="beta", y="alpha", hover_name="ticker",
        color="alpha sign",
        color_discrete_map={"positive α": "seagreen", "negative α": "firebrick"},
        hover_data=["sharpe", "total_return", "excess_return"],
        marginal_x="histogram", marginal_y="histogram",
        title=title, template="plotly_white",
        labels={"alpha": "annualized alpha", "beta": "beta vs benchmark"},
    )
    fig.add_hline(y=0.0, line_dash="dot", line_color="gray")
    fig.write_html(path, include_plotlyjs="cdn")
