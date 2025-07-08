import os
from dotenv import load_dotenv
load_dotenv()

OUTPUT_DIR = os.environ.get("LOG_DIR", './output')
LOG_DIR = os.path.join(OUTPUT_DIR, 'log')
FIGURE_DIR = os.path.join(OUTPUT_DIR, 'figures')

DATA_CACHE = os.environ.get('DATA_CACHE', './data_cache')
POLYGON_API_KEY = os.environ.get("POLYGON_API_KEY")
