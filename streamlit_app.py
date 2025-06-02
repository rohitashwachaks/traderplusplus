import pandas as pd
import streamlit as st
from typing import List

from core.backtester import Backtester
from core.data_loader import DataIngestionManager
from core.market_data import MarketData
from core.guardrails.base import Guardrail
from core.guardrails.trailing_stop_loss import TrailingStopLossGuardrail
from core.visualizer import plot_equity_curve, plot_drawdown, plotly_interactive_equity
from strategies.stock.base import StrategyFactory
from utils.metrics import summarize_metrics
from core.executors.backtest import BacktestExecutor
from core.executors.paper import PaperExecutor

st.set_page_config(layout="wide", page_title="Trader++ Strategy Lab")
st.title("📈 Trader++ Strategy Dashboard")

# Sidebar – Config
st.sidebar.title("⚙️ Backtest Settings")
use_guardrail = st.sidebar.checkbox("Enable Trailing Stop Loss", value=True)
stop_pct = st.sidebar.slider("Trailing Stop Loss %", 1, 20, 5) / 100.0
cash = st.sidebar.number_input("Starting Cash ($)", min_value=1000, value=100_000)

execution_mode = st.sidebar.selectbox("Execution Mode", ["backtest", "paper"], index=0)
slippage = st.sidebar.slider("Slippage (bps)", 0, 50, 10) / 10000.0  # 10 bps default

data_source = st.sidebar.selectbox("Data Source", ["yahoo", "alpaca", "polygon"], index=0)
tickers = st.sidebar.multiselect("Select Tickers", ["AAPL", "MSFT", "TSLA", "NVDA", "SPY"], default=["AAPL"])
start_date = st.sidebar.date_input("Start Date", value=pd.to_datetime("2023-01-01"))
end_date = st.sidebar.date_input("End Date", value=pd.to_datetime("2023-12-31"))

st.sidebar.title("📐 Strategy")
strategy_type = st.sidebar.selectbox("Strategy", ["momentum", "buy_n_hold"], index=0)
short_window = st.sidebar.slider("Short MA", 5, 50, 10)
long_window = st.sidebar.slider("Long MA", 10, 100, 30)

run_bt = st.sidebar.button("🚀 Run Backtest")

if run_bt:
    st.success("Running backtest...")
    ingestion = DataIngestionManager(use_cache=True, force_refresh=False, source=data_source)
    market_data = MarketData.from_ingestion(tickers, str(start_date), str(end_date), ingestion)
    strategy = StrategyFactory.create_strategy(strategy_type, short_window=short_window, long_window=long_window)
    guardrails: List[Guardrail] = []
    if use_guardrail:
        guardrails.append(TrailingStopLossGuardrail(stop_pct=stop_pct))
    from contracts.portfolio import Portfolio
    portfolio = Portfolio(
        name=f"{execution_mode.capitalize()}Portfolio",
        tickers=market_data.get_available_symbols(),
        starting_cash=cash,
        strategy=strategy,
        metadata={"source": f"{execution_mode.capitalize()}Executor"}
    )
    if execution_mode == "paper":
        executor = PaperExecutor(portfolio=portfolio, slippage=slippage, market_data=market_data)
    else:
        executor = BacktestExecutor(portfolio=portfolio, market_data=market_data, guardrails=guardrails)
    bt = Backtester(strategy=strategy, market_data=market_data, starting_cash=cash, executor=executor)
    bt.run(tickers, str(start_date), str(end_date))
    equity_curve = bt.get_equity_curve()
    trade_log = bt.get_trade_log()
    st.subheader("📋 Trade Log")
    st.dataframe(trade_log)
    st.subheader("💹 Equity Curve")
    st.line_chart(equity_curve.set_index("date")["net_worth"])
    st.subheader("📉 Drawdown")
    plot_drawdown(equity_curve)
    st.subheader("📊 Metrics")
    st.write(summarize_metrics(equity_curve, trade_log))
