from core.context import DataContext
from engine.runner import run
from reporting.interactive import write_equity_explorer
from strategies.buy_n_hold import BuyAndHold


def test_equity_explorer_writes_html(rising_prices, tmp_path):
    """The interactive explorer builds and writes a non-trivial HTML file from a real
    backtest result (synthetic data, no network)."""
    benchmark = rising_prices[["MSFT"]]
    res = run(BuyAndHold(), DataContext.from_prices(rising_prices), benchmark)

    out = tmp_path / "explorer.html"
    write_equity_explorer(res, rising_prices, "buy_n_hold", "MSFT", str(out))

    assert out.exists()
    assert out.stat().st_size > 1000
