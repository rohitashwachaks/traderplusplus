"""Point-in-time discipline for the new EDGAR panels: TTM EPS, shares, CIK overlay."""
import pandas as pd

from core.fundamentals import instant_series, ttm_eps_series
from data_ingestion.edgar_fetcher import _local_cik_overrides


def _q(start, end, filed, val):
    return {"start": start, "end": end, "filed": filed, "val": val}


# A clean two-year synthetic history: quarterly 10-Qs plus annual 10-Ks (Q4 never filed alone).
RECORDS = [
    _q("2021-01-01", "2021-03-31", "2021-05-01", 1.0),
    _q("2021-04-01", "2021-06-30", "2021-08-01", 1.5),
    _q("2021-07-01", "2021-09-30", "2021-11-01", 2.0),
    _q("2021-01-01", "2021-12-31", "2022-02-15", 6.5),   # FY21 → Q4'21 = 6.5 − 4.5 = 2.0
    _q("2022-01-01", "2022-03-31", "2022-05-01", 2.0),
    _q("2022-04-01", "2022-06-30", "2022-08-01", 2.5),
    _q("2022-07-01", "2022-09-30", "2022-11-01", 3.0),
    _q("2022-01-01", "2022-12-31", "2023-02-15", 10.0),  # FY22 → Q4'22 = 10 − 7.5 = 2.5
]


def test_ttm_q4_reconstruction_and_rolls():
    series = ttm_eps_series(RECORDS)

    # First TTM exists at the FY21 10-K: Q1–Q3 2021 + reconstructed Q4 = the annual itself.
    assert series.loc[pd.Timestamp("2022-02-15")] == 6.5
    # Each 2022 10-Q rolls one 2021 quarter out and one 2022 quarter in.
    assert series.loc[pd.Timestamp("2022-05-01")] == 6.5 - 1.0 + 2.0   # 7.5
    assert series.loc[pd.Timestamp("2022-08-01")] == 7.5 - 1.5 + 2.5   # 8.5
    assert series.loc[pd.Timestamp("2022-11-01")] == 8.5 - 2.0 + 3.0   # 9.5
    assert series.loc[pd.Timestamp("2023-02-15")] == 10.0              # FY22 10-K


def test_ttm_is_point_in_time_under_truncation():
    """The classic no-look-ahead test: dropping later filings must not change earlier values."""
    full = ttm_eps_series(RECORDS)
    cutoff = pd.Timestamp("2022-09-01")
    truncated = ttm_eps_series([r for r in RECORDS if pd.Timestamp(r["filed"]) <= cutoff])
    pd.testing.assert_series_equal(full.loc[:cutoff], truncated)


def test_ttm_ignores_restatements():
    restated = RECORDS + [
        _q("2021-01-01", "2021-03-31", "2023-06-01", 9.9),   # restated Q1'21 — must be ignored
    ]
    pd.testing.assert_series_equal(ttm_eps_series(restated), ttm_eps_series(RECORDS))


def test_ttm_skips_years_with_missing_quarters():
    missing_q2 = [r for r in RECORDS if r["filed"] != "2021-08-01"]
    series = ttm_eps_series(missing_q2)
    # FY21 Q4 can't be reconstructed (only 2 interim quarters) → no TTM at the FY21 10-K.
    assert pd.Timestamp("2022-02-15") not in series.index


def test_instant_series_ignores_stale_amendments():
    records = [
        {"end": "2021-03-31", "filed": "2021-05-01", "val": 100.0},
        {"end": "2021-06-30", "filed": "2021-08-01", "val": 110.0},
        {"end": "2021-03-31", "filed": "2021-09-15", "val": 999.0},  # amended 10-Q, stale as-of
    ]
    series = instant_series(records)
    assert list(series.values) == [100.0, 110.0]                     # amendment didn't regress


def test_local_cik_overrides_read_committed_csvs(tmp_path):
    csv = tmp_path / "u.csv"
    csv.write_text("Symbol,Security,CIK\nBRK.B,Berkshire,0001067983\nAAPL,Apple,320193\n")
    mapping = _local_cik_overrides(paths=(str(csv),))
    assert mapping == {"BRK-B": "0001067983", "AAPL": "0000320193"}  # normalized + zero-padded
