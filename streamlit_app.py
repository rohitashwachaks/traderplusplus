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
from strategies.stock.capm_portfolio import CAPMStrategy
from strategies.stock.momentum import MomentumStrategy
from strategies.stock.buy_n_hold import BuyNHoldStrategy
from utils.metrics import summarize_metrics


st.set_page_config(layout="wide", page_title="Trader++ Strategy Lab")
st.title("📈 Trader++ Strategy Dashboard")

# Sidebar – Config
st.sidebar.title("⚙️ Backtest Settings")
use_guardrail = st.sidebar.checkbox("Enable Trailing Stop Loss", value=True)
stop_pct = st.sidebar.slider("Trailing Stop Loss %", 1, 20, 5) / 100.0
cash = st.sidebar.number_input("Starting Cash ($)", min_value=1000, value=100_000)

data_source = st.sidebar.selectbox("Data Source", ["yahoo", "polygon"], index=0)
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

    # Data ingest
    ingestion = DataIngestionManager(use_cache=True, force_refresh=False, source=data_source)
    market_data = MarketData.from_ingestion(tickers, str(start_date), str(end_date), ingestion)

    # Strategy & Guardrails
    strategy = StrategyFactory.create_strategy(strategy_type, short_window=short_window, long_window=long_window)
    guardrails: List[Guardrail] = []
    if use_guardrail:
        guardrails.append(TrailingStopLossGuardrail(stop_pct=stop_pct))

    # Backtest
    bt = Backtester(strategy=strategy, market_data=market_data, starting_cash=cash, guardrails=guardrails)
    bt.run(tickers, str(start_date), str(end_date))

    equity_curve = bt.get_equity_curve()
    trade_log = bt.get_trade_log()

    # Show trades
    st.subheader("📋 Trade Log")
    st.dataframe(trade_log)

    # Trailing stops
    if "note" in trade_log.columns:
        ts_exits = trade_log[(trade_log["action"] == "SELL") & trade_log["note"].str.contains("Trailing", na=False)]
        if not ts_exits.empty:
            st.subheader("🔻 Trailing Stop Exits")
            st.dataframe(ts_exits)

    # Visuals
    st.subheader("📈 Equity Curve")
    fig_eq = plot_equity_curve(equity_curve['net_worth'])
    st.pyplot(fig_eq)

    st.subheader("📉 Drawdown")
    fig_dd = plot_drawdown(equity_curve['net_worth'])
    st.pyplot(fig_dd)

    st.subheader("📊 Performance Summary")
    summarize_metrics(equity_curve, trade_log, name="Portfolio")

    # Optional: Plotly chart
    if st.checkbox("🔍 Show Interactive Chart"):
        fig = plotly_interactive_equity(equity_curve['net_worth'], trade_log)
        st.plotly_chart(fig)
