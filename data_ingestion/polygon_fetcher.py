from polygon import RESTClient
import pandas as pd

from utils.config import POLYGON_API_KEY
from utils.utils import split_period

from tenacity import retry, stop_after_attempt, wait_exponential
import time


@retry(stop=stop_after_attempt(5), wait=wait_exponential(multiplier=1, min=5, max=300))
def fetch_with_retry(client, ticker, multiplier, timespan, start_date, end_date):
    try:
        polygon_response = client.list_aggs(
            ticker=ticker, multiplier=multiplier, timespan=timespan,
            from_=start_date, to=end_date, adjusted=True, sort='asc',
            limit=500
        )
        return polygon_response
    except Exception as e:
        print(f"Error: {e}. Retrying...")
        raise


def fetch_polygon_data_with_backoff(client, ticker, multiplier, timespan, start_date, end_date):
    while True:
        try:
            return fetch_with_retry(client, ticker, multiplier, timespan, start_date, end_date)
        except Exception as e:
            print(f"Rate limit hit. Waiting before retrying...")
            for remaining in range(300, 0, -1):
                print(f"Retrying in {remaining} seconds...", end="\r")
                time.sleep(1)


def fetch_polygon_data(ticker: str, start_date: str, end_date: str, interval: str) -> pd.DataFrame:
    """
    Fetch historical price data from Polygon for a given stock.

    Args:
        ticker (str): Stock ticker symbol.
        start_date (str): Start date in 'YYYY-MM-DD' format.
        end_date (str): End date in 'YYYY-MM-DD' format.
        interval (str): Price interval (e.g., '1m', '5m', '1h').
        api_key (str): Polygon API key.

    Returns:
        pd.DataFrame: DataFrame containing historical price data.
    """
    client = RESTClient(POLYGON_API_KEY)

    aggs = []
    multiplier, timespan = split_period(interval)

    polygon_response = fetch_polygon_data_with_backoff(
        client, ticker, multiplier, timespan, start_date, end_date
    )

    for a in polygon_response:
        aggs.append(a)

    df = pd.DataFrame(aggs)
    df["timestamp"] = pd.to_datetime(df["timestamp"], unit="ms")
    df.set_index("timestamp", inplace=True)
    df.columns = [k.capitalize() for k in df.columns]
    return df
