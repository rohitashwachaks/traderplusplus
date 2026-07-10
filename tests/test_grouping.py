"""Cross-industry grouping: rank-within-group, top-per-group, and the sector-neutral book."""
import numpy as np
import pandas as pd
import pytest

from core.context import DataContext
from engine.runner import run
from strategies import grouping
from strategies.sector_neutral_momentum import SectorNeutralMomentum


def _ctx(prices: pd.DataFrame, sectors: dict[str, str]) -> DataContext:
    meta = pd.DataFrame({"sector": pd.Series(sectors)}).reindex(prices.columns)
    members = pd.DataFrame(True, index=prices.index, columns=prices.columns)
    return DataContext(panels={"price": prices, "members": members}, meta=meta)


def test_rank_within_group_is_independent_per_group():
    feature = pd.DataFrame({"A": [10.0], "B": [5.0], "C": [9.0], "D": [1.0]})
    groups = pd.Series({"A": "tech", "B": "tech", "C": "energy", "D": "energy"})
    ranks = grouping.rank_within_group(feature, groups, ascending=False)
    # Best-in-group is rank 1 within each sector, not across the whole row.
    assert ranks.loc[0, "A"] == 1.0 and ranks.loc[0, "B"] == 2.0   # tech
    assert ranks.loc[0, "C"] == 1.0 and ranks.loc[0, "D"] == 2.0   # energy


def test_top_per_group_selects_one_from_each_group():
    feature = pd.DataFrame({"A": [10.0], "B": [5.0], "C": [9.0], "D": [1.0]})
    groups = pd.Series({"A": "tech", "B": "tech", "C": "energy", "D": "energy"})
    top = grouping.top_per_group(feature, groups, n=1, ascending=False)
    assert top.loc[0, "A"] and not top.loc[0, "B"]   # tech winner
    assert top.loc[0, "C"] and not top.loc[0, "D"]   # energy winner — book spans both


def test_unclassified_and_nan_feature_never_selected():
    feature = pd.DataFrame({"A": [10.0], "B": [np.nan], "C": [3.0]})
    groups = pd.Series({"A": "tech", "B": "tech"})   # C has no sector label
    top = grouping.top_per_group(feature, groups, n=5, ascending=False)
    assert top.loc[0, "A"]
    assert not top.loc[0, "B"]    # NaN feature
    assert not top.loc[0, "C"]    # unclassified


def test_classification_missing_key_raises():
    ctx = _ctx(pd.DataFrame({"A": [1.0]}), {"A": "tech"})
    with pytest.raises(KeyError, match="No classification 'sic2'"):
        ctx.classification("sic2")


def _two_sector_panel():
    dates = pd.date_range("2022-01-03", periods=90, freq="B")
    t = np.arange(90, dtype=float)
    # Tech names both rip; energy names both lag. A plain top-2 momentum book would hold
    # only the two tech names — the sector-neutral book must still hold one energy name.
    return pd.DataFrame({
        "TCH1": 100 * 1.004 ** t,
        "TCH2": 100 * 1.003 ** t,
        "NRG1": 100 * 1.0015 ** t,
        "NRG2": 100 * 1.0005 ** t,
    }, index=dates)


_SECTORS = {"TCH1": "tech", "TCH2": "tech", "NRG1": "energy", "NRG2": "energy"}


def test_sector_neutral_book_spans_both_sectors():
    prices = _two_sector_panel()
    weights = SectorNeutralMomentum(lookback=20, top_n=1).weights(_ctx(prices, _SECTORS))
    held = weights.iloc[-1]
    assert held[["TCH1", "TCH2"]].sum() > 0    # a tech name held
    assert held[["NRG1", "NRG2"]].sum() > 0    # AND an energy name — not tech-only
    assert held["TCH1"] > 0 and held["NRG1"] > 0   # the winner within each sector
    assert abs(held.sum() - 1.0) < 1e-9        # fully invested, equal weight


def test_sector_neutral_no_lookahead():
    """Truncating future bars must not change any past weight."""
    prices = _two_sector_panel()
    strat = SectorNeutralMomentum(lookback=20, top_n=1)
    full = strat.weights(_ctx(prices, _SECTORS))
    for i in (40, 60, 80):
        t = prices.index[i]
        sub = prices.loc[:t]
        trunc = strat.weights(_ctx(sub, _SECTORS))
        assert (full.loc[t] == trunc.loc[t]).all(), f"look-ahead at {t}"


def test_sector_neutral_runs_end_to_end():
    prices = _two_sector_panel()
    benchmark = pd.DataFrame({"SPY": np.linspace(100, 120, len(prices))}, index=prices.index)
    res = run(SectorNeutralMomentum(lookback=20, top_n=1), _ctx(prices, _SECTORS), benchmark)
    assert not res.prices["sector_neutral_momentum"].isna().any()


def test_build_context_classify_merges_edgar_sic(monkeypatch):
    """classify=True enriches meta with SIC from EDGAR and derives the 2-digit group."""
    from core.context import build_context
    from core.universe import ListUniverse

    dates = pd.date_range("2022-01-03", periods=5, freq="B")
    price = pd.DataFrame({"AAA": 100.0, "BBB": 50.0}, index=dates)

    class FakePrice:
        def load(self, tickers, start, end, **opts):
            return price[list(tickers)]

    monkeypatch.setattr("core.context._sources.get_source", lambda name: FakePrice())
    monkeypatch.setattr(
        "core.fundamentals.sic_meta",
        lambda tickers: pd.DataFrame(
            {"sic": ["3571", "1311"], "sic_description": ["Computers", "Crude Oil"]},
            index=["AAA", "BBB"]).reindex(tickers),
    )

    ctx = build_context(ListUniverse(["AAA", "BBB"]), "2022-01-01", "2022-02-01", classify=True)
    assert ctx.classification("sic2").to_dict() == {"AAA": "35", "BBB": "13"}
    assert ctx.meta.loc["AAA", "sic_description"] == "Computers"
