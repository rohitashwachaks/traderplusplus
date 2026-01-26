import streamlit as st
import requests
import os

try:
    API_BASE_URL = st.secrets.get("API_BASE_URL", "http://localhost:8000/api")
except:
    API_BASE_URL = os.getenv("API_BASE_URL", "http://localhost:8000/api")

st.header("📚 Strategy Library")

st.markdown("Browse available trading strategies and their configurations.")

try:
    response = requests.get(f"{API_BASE_URL}/strategies/list", timeout=5)
    
    if response.status_code == 200:
        strategies = response.json()
        
        if strategies:
            categories = {}
            for strategy in strategies:
                category = strategy.get("category", "Other")
                if category not in categories:
                    categories[category] = []
                categories[category].append(strategy)
            
            for category, strats in categories.items():
                st.subheader(f"📁 {category}")
                
                for strategy in strats:
                    with st.expander(f"**{strategy['name'].upper()}**"):
                        st.markdown(f"_{strategy['description']}_")
                        
                        if strategy.get('parameters'):
                            st.markdown("**Parameters:**")
                            for param, details in strategy['parameters'].items():
                                default = details.get('default', 'None')
                                param_type = details.get('type', 'Any')
                                st.write(f"- `{param}`: {param_type} (default: {default})")
                        else:
                            st.write("No configurable parameters")
                
                st.markdown("---")
        else:
            st.info("No strategies found")
    
    else:
        st.error(f"Failed to load strategies: {response.text}")

except requests.exceptions.ConnectionError:
    st.error("❌ Cannot connect to API. Make sure the backend is running.")
    
    st.markdown("### Available Strategies (Fallback)")
    st.markdown("""
    - **momentum** - Momentum-based trading strategy
    - **buy_n_hold** - Buy and hold strategy
    - **mean_reversion** - Mean reversion strategy
    - **rsi_strategy** - RSI-based strategy
    """)

except Exception as e:
    st.error(f"Error: {str(e)}")
