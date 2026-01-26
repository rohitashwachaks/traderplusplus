import streamlit as st
import requests
from datetime import datetime, timedelta
import time
import os

try:
    API_BASE_URL = st.secrets.get("API_BASE_URL", "http://localhost:8000/api")
except:
    API_BASE_URL = os.getenv("API_BASE_URL", "http://localhost:8000/api")

st.header("🚀 Run Backtest")

st.markdown("Configure and run a backtest against historical data.")

with st.form("backtest_form"):
    col1, col2 = st.columns(2)
    
    with col1:
        strategy = st.selectbox(
            "Strategy",
            ["momentum", "buy_n_hold", "mean_reversion", "rsi_strategy"],
            help="Select a trading strategy"
        )
        
        tickers = st.text_input(
            "Tickers",
            value="AAPL",
            help="Comma-separated list (e.g., AAPL,MSFT,GOOGL)"
        )
        
        cash = st.number_input(
            "Starting Cash ($)",
            min_value=1000.0,
            value=100000.0,
            step=1000.0
        )
        
        benchmark = st.text_input(
            "Benchmark",
            value="SPY",
            help="Benchmark ticker for comparison"
        )
    
    with col2:
        start_date = st.date_input(
            "Start Date",
            value=datetime.now() - timedelta(days=365*3)
        )
        
        end_date = st.date_input(
            "End Date",
            value=datetime.now()
        )
        
        interval = st.selectbox(
            "Interval",
            ["1d", "1h", "1wk", "1mo"],
            index=0
        )
        
        source = st.selectbox(
            "Data Source",
            ["yahoo", "polygon", "alpaca"],
            index=0
        )
    
    col3, col4 = st.columns(2)
    
    with col3:
        guardrail = st.selectbox(
            "Guardrail (Optional)",
            [None, "trailing_stop_loss"],
            help="Risk management guardrail"
        )
    
    with col4:
        refresh = st.checkbox(
            "Force Data Refresh",
            value=False,
            help="Ignore cached data"
        )
    
    submitted = st.form_submit_button("🚀 Run Backtest", type="primary")

if submitted:
    config = {
        "strategy": strategy,
        "tickers": tickers,
        "start_date": start_date.strftime("%Y-%m-%d"),
        "end_date": end_date.strftime("%Y-%m-%d"),
        "cash": cash,
        "benchmark": benchmark if benchmark else None,
        "guardrail": guardrail,
        "interval": interval,
        "source": source,
        "refresh": refresh
    }
    
    with st.spinner("Submitting backtest job..."):
        try:
            response = requests.post(
                f"{API_BASE_URL}/backtest/run",
                json=config,
                timeout=10
            )
            
            if response.status_code == 200:
                result = response.json()
                job_id = result["job_id"]
                
                st.success(f"✅ Backtest job submitted! Job ID: `{job_id}`")
                
                progress_bar = st.progress(0)
                status_text = st.empty()
                
                max_wait = 300
                elapsed = 0
                
                while elapsed < max_wait:
                    status_response = requests.get(
                        f"{API_BASE_URL}/backtest/{job_id}/status",
                        timeout=5
                    )
                    
                    if status_response.status_code == 200:
                        status_data = status_response.json()
                        status = status_data["status"]
                        progress = status_data.get("progress", 0.0)
                        
                        progress_bar.progress(progress)
                        status_text.text(f"Status: {status} ({progress*100:.0f}%)")
                        
                        if status == "completed":
                            st.success("🎉 Backtest completed!")
                            st.info(f"View results in the **Results Viewer** page with Job ID: `{job_id}`")
                            break
                        elif status == "failed":
                            error = status_data.get("error", "Unknown error")
                            st.error(f"❌ Backtest failed: {error}")
                            break
                    
                    time.sleep(2)
                    elapsed += 2
                
                if elapsed >= max_wait:
                    st.warning("⏱️ Backtest is taking longer than expected. Check Results Viewer later.")
            
            else:
                st.error(f"❌ Failed to submit backtest: {response.text}")
        
        except requests.exceptions.ConnectionError:
            st.error("❌ Cannot connect to API. Make sure the backend is running on `http://localhost:8000`")
        except Exception as e:
            st.error(f"❌ Error: {str(e)}")

st.markdown("---")
st.markdown("**Note**: Make sure the FastAPI backend is running before submitting jobs.")
