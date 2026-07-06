"""The canonical price store: additive, gap-only fetching, idempotent."""
import numpy as np
import pandas as pd
import pytest

from core.store import PriceStore


def _ohlcv(start: str, end: str) -> pd.DataFrame:
    dates = pd.date_range(start, end, freq="B")
    base = 100.0 + np.arange(len(dates), dtype=float)
    return pd.DataFrame(
        {"Open": base, "High": base + 1, "Low": base - 1, "Close": base, "Volume": 1e6},
        index=dates,
    )


class RecordingFetcher:
    """Serves synthetic bars and records every (ticker, start, end) call."""

    def __init__(self):
        self.calls: list[tuple[str, str, str]] = []

    def __call__(self, ticker: str, start: str, end: str) -> pd.DataFrame:
        self.calls.append((ticker, start, end))
        return _ohlcv(start, end)


@pytest.fixture
def store(tmp_path):
    fetcher = RecordingFetcher()
    s = PriceStore(root=str(tmp_path / "data_store"), fetcher=fetcher)
    s.fetcher = fetcher  # expose for assertions
    return s


def test_ensure_then_load_round_trips(store):
    store.ensure(["AAPL"], "2020-01-01", "2020-03-31")
    data = store.load(["AAPL"], "2020-01-01", "2020-03-31")
    expected = _ohlcv("2020-01-01", "2020-03-31")
    pd.testing.assert_frame_equal(
        data["AAPL"], expected.rename_axis("date"), check_freq=False
    )


def test_second_ensure_is_a_no_op(store):
    store.ensure(["AAPL"], "2020-01-01", "2020-03-31")
    calls_after_first = len(store.fetcher.calls)
    store.ensure(["AAPL"], "2020-01-01", "2020-03-31")
    assert len(store.fetcher.calls) == calls_after_first  # nothing refetched


def test_widening_the_window_fetches_only_the_gaps(store):
    store.ensure(["AAPL"], "2020-06-01", "2020-06-30")
    store.fetcher.calls.clear()
    store.ensure(["AAPL"], "2020-01-01", "2020-12-31")

    assert store.fetcher.calls == [
        ("AAPL", "2020-01-01", "2020-05-31"),   # head gap only
        ("AAPL", "2020-07-01", "2020-12-31"),   # tail gap only
    ]
    data = store.load(["AAPL"], "2020-01-01", "2020-12-31")["AAPL"]
    assert not data.index.duplicated().any()
    assert data.index.min() == pd.Timestamp("2020-01-01")


def test_weekend_only_gap_never_refetches(store):
    # 2020-07-03 is a Friday(holiday-adjacent); requesting through the following Sunday
    # after having covered through Friday must not trigger a fetch for the weekend.
    store.ensure(["AAPL"], "2020-06-01", "2020-07-03")
    store.fetcher.calls.clear()
    store.ensure(["AAPL"], "2020-06-01", "2020-07-03")
    assert store.fetcher.calls == []


def test_reingest_overlap_prefers_new_data(store):
    store.ingest("AAPL", _ohlcv("2020-01-01", "2020-01-31"),
                 source="yahoo", start="2020-01-01", end="2020-01-31")
    restated = _ohlcv("2020-01-01", "2020-01-31") * 0.5  # a split restates history
    store.ingest("AAPL", restated, source="yahoo", start="2020-01-01", end="2020-01-31")
    data = store.load(["AAPL"], "2020-01-01", "2020-01-31")["AAPL"]
    assert data["Close"].iloc[0] == pytest.approx(50.0)  # new data won


def test_source_mismatch_raises(store):
    store.ensure(["AAPL"], "2020-01-01", "2020-01-31", source="yahoo")
    with pytest.raises(ValueError, match="One vendor per ticker"):
        store.ensure(["AAPL"], "2020-01-01", "2020-01-31", source="polygon")


def test_load_unknown_ticker_raises(store):
    with pytest.raises(KeyError, match="not in the price store"):
        store.load(["ZZZZ"], "2020-01-01", "2020-01-31")


def test_no_data_window_is_recorded_not_refetched(tmp_path):
    def failing_fetcher(ticker, start, end):
        raise ValueError(f"No data returned for {ticker}")

    store = PriceStore(root=str(tmp_path / "ds"), fetcher=failing_fetcher)
    store.ensure(["GHOST"], "2020-01-01", "2020-01-31")   # logged, coverage recorded
    assert store.load(["GHOST"], "2020-01-01", "2020-01-31")["GHOST"].empty

    def exploding_fetcher(ticker, start, end):
        raise AssertionError("should not refetch a recorded empty window")

    store2 = PriceStore(root=str(tmp_path / "ds"), fetcher=exploding_fetcher)
    store2.ensure(["GHOST"], "2020-01-01", "2020-01-31")  # no fetch attempted
