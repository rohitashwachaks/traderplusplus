import streamlit as st
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

st.set_page_config(
    page_title="Trader++ Dashboard",
    page_icon="📈",
    layout="wide",
    initial_sidebar_state="expanded"
)

st.title("📈 Trader++ Dashboard")
st.markdown("---")

pages = {
    "🏠 Home": "pages/home.py",
    "🚀 Run Backtest": "pages/backtest_runner.py",
    "📊 Results Viewer": "pages/results_viewer.py",
    "💼 Portfolio Monitor": "pages/portfolio_monitor.py",
    "📚 Strategy Library": "pages/strategy_library.py",
}

st.sidebar.title("Navigation")
selection = st.sidebar.radio("Go to", list(pages.keys()))

page_file = pages[selection]
page_path = Path(__file__).parent / page_file

if page_path.exists():
    with open(page_path) as f:
        code = f.read()
        exec(code, {"st": st, "__file__": str(page_path)})
else:
    st.error(f"Page not found: {page_file}")
