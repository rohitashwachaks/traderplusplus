"""Research bed: sweep a single-asset rule across a universe and study the distribution of
outcomes — the antidote to validating a strategy on one cherry-picked ticker."""
from research.report import write_distribution_report
from research.sweep import sweep_universe

__all__ = ["sweep_universe", "write_distribution_report"]
