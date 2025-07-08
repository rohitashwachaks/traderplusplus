import os
import pandas as pd
import requests
from dotenv import load_dotenv


def fetch_alpaca_data(ticker: str, start_date: str, end_date: str, interval: str = "1Day") -> pd.DataFrame:
    """
    Fetch historical OHLCV data from Alpaca for a given ticker and date range.
    Requires ALPACA_API_KEY and ALPACA_API_SECRET in environment or .env.
    """
    load_dotenv()
    api_key = os.getenv("ALPACA_API_KEY")
    api_secret = os.getenv("ALPACA_API_SECRET")
    base_url = os.getenv("ALPACA_BASE_URL", "https://paper-api.alpaca.markets")
    data_url = base_url.replace("paper-api", "data-api").replace("/v2", "")
    if not api_key or not api_secret:
        raise ValueError("Missing Alpaca API credentials.")

    session = requests.Session()
    session.headers.update({
        "APCA-API-KEY-ID": api_key,
        "APCA-API-SECRET-KEY": api_secret
    })
    endpoint = f"{data_url}/v2/stocks/{ticker}/bars"
    params = {
        "start": start_date,
        "end": end_date,
        "timeframe": interval,
        "adjustment": "all",
        "limit": 10000
    }
    resp = session.get(endpoint, params=params)
    resp.raise_for_status()
    bars = resp.json().get("bars", [])
    if not bars:
        return pd.DataFrame()
    df = pd.DataFrame(bars)
    df.rename(columns={"t": "Date", "o": "Open", "h": "High", "l": "Low", "c": "Close", "v": "Volume"}, inplace=True)
    df["Date"] = pd.to_datetime(df["Date"], unit="s")
    df.set_index("Date", inplace=True)
    return df[["Open", "High", "Low", "Close", "Volume"]]
