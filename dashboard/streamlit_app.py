import streamlit as st
from core.backtester import Backtester
from core.data_loader import load_price_data
from strategies.strategy_factory import StrategyFactory
from core.visualizer import plot_equity_curve, plot_drawdown
from utils.metrics import summarize_metrics


st.set_page_config(layout="wide", page_title="Trader++ Strategy Lab")

st.title("📈 Trader++ Strategy Dashboard")

# Inputs
symbols = st.multiselect("Select Symbols", ["AAPL", "MSFT", "TSLA", "NVDA", "SPY"], default=["AAPL"])
start_date = st.date_input("Start Date", value=pd.to_datetime("2023-01-01"))
end_date = st.date_input("End Date", value=pd.to_datetime("2023-12-31"))

# Strategy parameters
strategy_type = st.selectbox("Select Strategy", ["momentum"])
short_window = st.slider("Short Moving Average", 5, 50, 10)
long_window = st.slider("Long Moving Average", 10, 100, 30)

run_bt = st.button("Run Backtest")

if run_bt:
    st.success("Running backtest...")
    strategy = StrategyFactory.create_strategy(strategy_type, short_window=short_window, long_window=long_window)
    bt = Backtester(data_loader=load_price_data)
    bt.run(strategies={strategy_type: strategy}, symbols=symbols, start_date=str(start_date), end_date=str(end_date))

    # Individual strategy results
    for res in bt.get_results():
        st.subheader(f"{res.strategy_name} on {res.symbol}")
        plot_equity_curve(res.equity_curve, title="Equity Curve")
        plot_drawdown(res.equity_curve, title="Drawdown")
        summarize_metrics(res.equity_curve, res.trades, name=f"{res.strategy_name} on {res.symbol}")
        st.dataframe(res.trades)

    # Portfolio view
    st.subheader("📊 Portfolio View")
    portfolio_curve = bt.summarize_portfolio()
    plot_equity_curve(portfolio_curve, title="Total Portfolio Equity Curve")
    plot_drawdown(portfolio_curve, title="Total Portfolio Drawdown")