import os

OUTPUT_DIR = os.environ.get("LOG_DIR", './output')
LOG_DIR = os.path.join(OUTPUT_DIR, 'log')
FIGURE_DIR = os.path.join(OUTPUT_DIR, 'figures')
