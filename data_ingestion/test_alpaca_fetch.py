import os
from dotenv import load_dotenv
from data_ingestion.alpaca_fetcher import fetch_alpaca_data

if __name__ == "__main__":
    load_dotenv()
    # Set your test parameters
    ticker = "AAPL"
    start_date = "2024-01-01"
    end_date = "2024-01-31"
    print(f"Fetching Alpaca data for {ticker} from {start_date} to {end_date}...")
    df = fetch_alpaca_data(ticker, start_date, end_date)
    print(df.head())
    print(f"Rows: {len(df)} | Columns: {list(df.columns)}")
    print(f"Date range: {df.index.min()} to {df.index.max()}")
