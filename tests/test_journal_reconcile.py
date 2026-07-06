"""Paper-trading audit trail: journal round-trips; reconciliation catches every drift kind."""
import pytest

from engine import journal
from engine.paper import reconcile


def test_journal_appends_and_reads_back(tmp_path):
    path = str(tmp_path / "journal.jsonl")
    journal.record(path, "preview", {"orders": []})
    journal.record(path, "executed", {"orders": [{"ticker": "AAPL", "side": "buy", "qty": 5}]})
    journal.record(path, "reconciliation", {"rows": []})

    events = journal.read(path)
    assert [e["kind"] for e in events] == ["preview", "executed", "reconciliation"]
    assert journal.last(path, "executed")["orders"][0]["ticker"] == "AAPL"
    assert journal.last(path, "missing-kind") is None


def test_reconcile_flags_fills_partials_missing_and_unplanned():
    planned = [
        {"ticker": "AAPL", "side": "buy", "qty": 10},    # fully filled, 10bps worse
        {"ticker": "MSFT", "side": "sell", "qty": 4},    # partial
        {"ticker": "NVDA", "side": "buy", "qty": 3},     # never reached the broker
    ]
    broker_orders = [
        {"symbol": "AAPL", "side": "buy", "qty": 10, "filled_qty": 10,
         "filled_avg_price": 100.10, "status": "filled"},
        {"symbol": "MSFT", "side": "sell", "qty": 4, "filled_qty": 2,
         "filled_avg_price": 50.0, "status": "partially_filled"},
        {"symbol": "TSLA", "side": "buy", "qty": 1, "filled_qty": 1,
         "filled_avg_price": 200.0, "status": "filled"},   # journal knows nothing of this
    ]
    prices = {"AAPL": 100.0, "MSFT": 50.0, "NVDA": 400.0}

    report = reconcile(planned, broker_orders, prices).set_index(["ticker", "side"])

    aapl = report.loc[("AAPL", "buy")]
    assert aapl["status"] == "filled"
    assert aapl["slippage_bps"] == pytest.approx(10.0)  # bought 10bps above reference

    assert report.loc[("MSFT", "sell"), "status"] == "partial"
    assert report.loc[("NVDA", "buy"), "status"] == "missing"
    assert report.loc[("TSLA", "buy"), "status"] == "unplanned"


def test_reconcile_sell_slippage_sign():
    planned = [{"ticker": "AAPL", "side": "sell", "qty": 10}]
    broker_orders = [{"symbol": "AAPL", "side": "sell", "qty": 10, "filled_qty": 10,
                      "filled_avg_price": 99.0, "status": "filled"}]
    report = reconcile(planned, broker_orders, {"AAPL": 100.0})
    # Selling 1% below reference costs ~100bps — the sign must say "cost", not "gain".
    assert report["slippage_bps"].iloc[0] == pytest.approx(100.0)
