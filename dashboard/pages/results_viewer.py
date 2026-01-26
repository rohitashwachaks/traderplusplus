import streamlit as st
import requests
import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import os

try:
    API_BASE_URL = st.secrets.get("API_BASE_URL", "http://localhost:8000/api")
except:
    API_BASE_URL = os.getenv("API_BASE_URL", "http://localhost:8000/api")

st.header("📊 Backtest Results Viewer")

try:
    jobs_response = requests.get(f"{API_BASE_URL}/backtest/jobs", timeout=5)
    
    if jobs_response.status_code == 200:
        jobs_data = jobs_response.json()
        jobs = jobs_data.get("jobs", [])
        
        if jobs:
            job_options = {
                f"{job['job_id'][:8]}... ({job['status']}) - {job['config'].get('strategy', 'N/A')}": job['job_id']
                for job in jobs
            }
            
            selected_job = st.selectbox(
                "Select Backtest Job",
                options=list(job_options.keys())
            )
            
            job_id = job_options[selected_job]
        else:
            st.info("No backtest jobs found. Run a backtest first!")
            job_id = None
    else:
        st.warning("Could not fetch jobs list")
        job_id = st.text_input("Enter Job ID manually")

except requests.exceptions.ConnectionError:
    st.error("❌ Cannot connect to API. Make sure the backend is running.")
    job_id = st.text_input("Enter Job ID manually")
except Exception as e:
    st.error(f"Error: {str(e)}")
    job_id = None

if job_id and st.button("📥 Load Results", type="primary"):
    try:
        results_response = requests.get(
            f"{API_BASE_URL}/backtest/{job_id}/results",
            timeout=10
        )
        
        if results_response.status_code == 200:
            results = results_response.json()
            
            st.success("✅ Results loaded successfully!")
            
            col1, col2, col3, col4 = st.columns(4)
            
            with col1:
                st.metric(
                    "Starting Cash",
                    f"${results['starting_cash']:,.2f}"
                )
            
            with col2:
                st.metric(
                    "Final Net Worth",
                    f"${results['final_net_worth']:,.2f}",
                    delta=f"{results['total_return']:.2f}%"
                )
            
            with col3:
                sharpe = results['metrics'].get('sharpe_ratio', 0)
                st.metric("Sharpe Ratio", f"{sharpe:.2f}")
            
            with col4:
                max_dd = results['metrics'].get('max_drawdown', 0)
                st.metric("Max Drawdown", f"{max_dd:.2f}%")
            
            st.markdown("---")
            
            tab1, tab2, tab3 = st.tabs(["📈 Equity Curve", "📋 Trade Log", "📊 Metrics"])
            
            with tab1:
                st.subheader("Equity Curve vs Benchmark")
                
                equity_df = pd.DataFrame(results['equity_curve'])
                
                if 'date' in equity_df.columns:
                    equity_df['date'] = pd.to_datetime(equity_df['date'])
                
                fig = go.Figure()
                
                fig.add_trace(go.Scatter(
                    x=equity_df['date'] if 'date' in equity_df.columns else equity_df.index,
                    y=equity_df['net_worth'],
                    mode='lines',
                    name='Portfolio',
                    line=dict(color='#1f77b4', width=2)
                ))
                
                if 'benchmark' in equity_df.columns:
                    fig.add_trace(go.Scatter(
                        x=equity_df['date'] if 'date' in equity_df.columns else equity_df.index,
                        y=equity_df['benchmark'],
                        mode='lines',
                        name='Benchmark',
                        line=dict(color='#ff7f0e', width=2, dash='dash')
                    ))
                
                fig.update_layout(
                    title="Portfolio Performance",
                    xaxis_title="Date",
                    yaxis_title="Value ($)",
                    hovermode='x unified',
                    height=500
                )
                
                st.plotly_chart(fig, use_container_width=True)
            
            with tab2:
                st.subheader("Trade Log")
                
                trade_df = pd.DataFrame(results['trade_log'])
                
                if not trade_df.empty:
                    st.dataframe(trade_df, use_container_width=True, height=400)
                    
                    csv = trade_df.to_csv(index=False)
                    st.download_button(
                        "📥 Download Trade Log",
                        csv,
                        f"trade_log_{job_id[:8]}.csv",
                        "text/csv"
                    )
                else:
                    st.info("No trades executed")
            
            with tab3:
                st.subheader("Performance Metrics")
                
                metrics = results['metrics']
                
                col1, col2 = st.columns(2)
                
                with col1:
                    st.markdown("**Returns**")
                    st.write(f"Total Return: {results['total_return']:.2f}%")
                    st.write(f"CAGR: {metrics.get('cagr', 0):.2f}%")
                    st.write(f"Volatility: {metrics.get('volatility', 0):.2f}%")
                
                with col2:
                    st.markdown("**Risk Metrics**")
                    st.write(f"Sharpe Ratio: {metrics.get('sharpe_ratio', 0):.2f}")
                    st.write(f"Sortino Ratio: {metrics.get('sortino_ratio', 0):.2f}")
                    st.write(f"Max Drawdown: {metrics.get('max_drawdown', 0):.2f}%")
                
                st.markdown("**Benchmark Comparison**")
                st.write(f"Alpha: {metrics.get('alpha', 0):.4f}")
                st.write(f"Beta: {metrics.get('beta', 0):.2f}")
        
        elif results_response.status_code == 400:
            st.warning("⏳ Backtest not completed yet. Please wait and try again.")
        else:
            st.error(f"❌ Failed to load results: {results_response.text}")
    
    except requests.exceptions.ConnectionError:
        st.error("❌ Cannot connect to API")
    except Exception as e:
        st.error(f"❌ Error: {str(e)}")
