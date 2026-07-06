import os
from dotenv import load_dotenv
load_dotenv()

OUTPUT_DIR = os.environ.get("LOG_DIR", './output')
LOG_DIR = os.path.join(OUTPUT_DIR, 'log')
FIGURE_DIR = os.path.join(OUTPUT_DIR, 'figures')

DATA_CACHE = os.environ.get('DATA_CACHE', './data_cache')
DATA_STORE = os.environ.get('DATA_STORE', './data_store')
POLYGON_API_KEY = os.environ.get("POLYGON_API_KEY")

ALPACA_API_KEY = os.environ.get("ALPACA_API_KEY")
ALPACA_API_SECRET = os.environ.get("ALPACA_API_SECRET")
ALPACA_BASE_URL = os.environ.get("ALPACA_BASE_URL", "https://paper-api.alpaca.markets")
