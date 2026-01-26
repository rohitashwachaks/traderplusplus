import streamlit as st
from datetime import datetime

st.header("Welcome to Trader++ 🚀")

st.markdown("""
### Your Modular Trading Engine

Trader++ is a full-fledged quant trading engine built for realistic portfolio simulation and strategy development.

#### Quick Start
1. **📚 Browse Strategies** - Explore available trading strategies
2. **🚀 Run Backtest** - Test strategies against historical data
3. **📊 View Results** - Analyze performance metrics and equity curves
4. **💼 Monitor Portfolio** - Track live positions and performance

#### Features
- ✅ Event-driven backtesting
- ✅ Multi-asset portfolio management
- ✅ Advanced risk guardrails
- ✅ Benchmark comparison
- ✅ Real-time monitoring (coming soon)

---
""")

col1, col2, col3 = st.columns(3)

with col1:
    st.metric("API Status", "🟢 Online", "Healthy")

with col2:
    st.metric("Active Jobs", "0", "No running backtests")

with col3:
    st.metric("Strategies", "6+", "Available")

st.markdown("---")

st.info("💡 **Tip**: Start by running a backtest from the sidebar menu!")

st.markdown(f"**Last Updated**: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
