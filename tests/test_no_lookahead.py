from strategies.momentum import Momentum


def test_momentum_weight_at_t_ignores_future(choppy_prices):
    """A weight on date t must depend only on data through t: truncating everything after
    t must not change the weight at t. This fails if the strategy peeks ahead."""
    strat = Momentum(short_window=3, long_window=10)
    full = strat.weights(choppy_prices)

    # Probe several interior dates, past the lookback warm-up.
    for i in (40, 60, 80, 100):
        t = choppy_prices.index[i]
        truncated = strat.weights(choppy_prices.loc[:t])
        assert (full.loc[t] == truncated.loc[t]).all(), f"look-ahead detected at {t}"


def test_momentum_acts_on_next_bar(choppy_prices):
    """The crossover decision on day t should take effect no earlier than t+1 (one-bar
    lag), so the very first row is always flat."""
    weights = Momentum().weights(choppy_prices)
    assert weights.iloc[0].sum() == 0.0
