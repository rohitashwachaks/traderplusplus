"""Importing this package registers all built-in strategies."""
from strategies import (  # noqa: F401  (registers)
    buy_n_hold,
    cross_sectional_momentum,
    dual_window_momentum,
    long_short_pe,
    momentum,
)
from strategies.base import available, create
