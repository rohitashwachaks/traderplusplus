"""Cross-sectional group operations — the primitive behind cross-industry strategies.

A group label per ticker (sector, sub-industry, 2-digit SIC, …) plus a wide feature panel is
all you need to rank *within* each group and select the best per group — i.e. spread a signal
across industries instead of letting one hot sector dominate. Everything here is pure
column-wise work per date: it carries no time dependence, so a strategy composing it keeps
whatever no-look-ahead guarantee its feature panel already has.
"""
import numpy as np
import pandas as pd


def group_series(ctx, by: str) -> pd.Series:
    """Ticker → group label, aligned to ``ctx.price`` columns (see :meth:`DataContext.classification`)."""
    return ctx.classification(by)


def rank_within_group(feature: pd.DataFrame, groups: pd.Series,
                      *, ascending: bool = False) -> pd.DataFrame:
    """Rank each name **against only its own group**, per date (1 = best in group).

    ``ascending=False`` ranks high values best (momentum); ``True`` ranks low values best
    (cheap P/E). Names with a missing group label or a NaN feature get a NaN rank — they are
    never selected. Columns not present in ``feature`` are ignored.
    """
    out = pd.DataFrame(np.nan, index=feature.index, columns=feature.columns)
    for label, members in groups.groupby(groups).groups.items():  # NaN labels dropped by groupby
        cols = [c for c in members if c in feature.columns]
        if cols:
            out[cols] = feature[cols].rank(axis=1, ascending=ascending, method="first")
    return out


def top_per_group(feature: pd.DataFrame, groups: pd.Series, n: int,
                  *, ascending: bool = False) -> pd.DataFrame:
    """Boolean mask selecting the top ``n`` names in each group each date.

    A group with fewer than ``n`` valid names contributes all of them. Used to build a
    book that holds names from *every* industry, not just the strongest one overall.
    """
    if n < 1:
        raise ValueError("n must be >= 1")
    ranks = rank_within_group(feature, groups, ascending=ascending)
    return ranks.le(n) & feature.notna()
