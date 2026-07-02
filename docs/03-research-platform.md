# Research Platform — universe-first, point-in-time backtesting

How Trader++ grows from a single-strategy backtester into a research bed for *building, screening, and
trustworthily backtesting* ideas. For day-to-day coding rules see `AGENT.md`; for the broader trajectory see
`docs/00-direction.md`.

## Why this exists — the bias reckoning

The original engine had a strong **no-look-ahead** discipline (`shift(1)`, truncation tests). That guards
exactly one bias — temporal leakage in a price signal — and it quietly created a false sense of safety while
three deeper biases went unchallenged:

- **Selection bias.** Backtesting a hand-picked surviving ticker (momentum on AAPL, or Home Depot today)
  answers nothing: the *choice of ticker* is the cheat — you only picked it because you know it won. A rule
  must be tested **cross-sectionally over a whole universe**, not on one name.
- **Survivorship bias.** Using *today's* index members to backtest the past silently deletes the names that
  were dropped or delisted — usually the losers — flattering every result.
- **Point-in-time fundamentals.** A P/E strategy can only be validated with the P/E that was *public* on each
  past date (its filing date), not today's snapshot. Today's number in a 2021 decision is future knowledge.

The platform is designed so these are structurally hard to commit, and so any residual bias is **labeled on
every report**. A labeled-approximate backtest is honest; an unlabeled one is the cardinal sin.

## The core reframe

> **The unit of backtesting is a *rule over a point-in-time universe*, not a strategy over a ticker.**

A single ticker is just the degenerate N=1 case. Momentum is not "does momentum work on AAPL" — it is "if I
rank the whole universe by momentum each period and hold the top names, do I beat the benchmark?"

## Architecture

Pipeline (additions in **bold**):

```text
universe (membership) + prices + EDGAR fundamentals/SIC
  → core/data_loader parquet cache
  → **DataContext**  (price · members · meta · fundamental(name) — all dates × tickers, point-in-time)
  → strategy.weights(ctx)  — cross-sectional rank/select/weight within the in-universe names
  → guardrails (risk overlays)
  → engine/runner → bt  (single backtest OR **research/ compare/sweep** over many configs)
  → reporting + **research report**  (bias-stamped metrics, overlaid explorer, sweep heatmap)
```

### Keystone: `DataContext` (`core/context.py`, new)

Every strategy receives one bundle of four panels on the same `dates × tickers` grid, so strategies do pure
column-wise ranking and never reason about time. The bias protections live in **how the panels are built**, not
in the strategy:

```python
@dataclass
class DataContext:
    price:   pd.DataFrame   # close panel (reuse core/price_panel.to_price_panel)
    members: pd.DataFrame   # bool: was this name in the universe on this date (membership mask)
    meta:    pd.DataFrame   # tickers × {sector, sic, ...} static classification
    def fundamental(self, name: str) -> pd.DataFrame: ...   # point-in-time panel, e.g. "pe"
```

`ctx.fundamental("pe").where(ctx.members)` is the entire survivorship + universe guard in one line. On the
labeled-biased start `members` is all-`True`; when a historical-membership feed lands later, that same line
starts doing real work with **zero strategy changes**.

### Strategy interface: `weights(prices)` → `weights(ctx)`

The hinge of the whole platform. All strategies receive a `DataContext`; the existing `buy_n_hold`, `momentum`,
and `xs_momentum` change ~3 lines to read `ctx.price`. One interface, no dual paths. The no-look-ahead contract
extends unchanged: truncating `ctx` after date `t` (price *and* fundamentals) must not change any weight at or
before `t`.

Example — a long/short P/E book, expressed once and reused for backtest, screen, and live:

```python
@register("ls_pe")
class LongShortPE(TargetWeightStrategy):
    reconstitution_freq = "Q"            # fundamentals only move on filings — match the cadence
    def __init__(self, n: int = 5): self.n = n

    def weights(self, ctx: DataContext) -> pd.DataFrame:
        pe = ctx.fundamental("pe").where(ctx.members)    # only in-universe names, that day
        pe = pe.where(pe > 0)                            # negative P/E is meaningless
        rank = pe.rank(axis=1)                           # cheapest = lowest rank
        longs, shorts = rank.le(self.n), rank.ge(rank.max(axis=1).values[:, None] - self.n + 1)
        w = longs.astype(float) / self.n - shorts.astype(float) / self.n   # +1/N, −1/N → sum ≈ 0
        return w.shift(1).fillna(0.0)                    # decide t, act t+1
```

### Data sources — one source of truth

- **Prices:** existing `data_ingestion/*` fetchers + `core/data_loader.py` parquet cache (MD5 key per
  ticker/range/interval/source). Unchanged.
- **Fundamentals + SIC: EDGAR only** (`data_ingestion/edgar_fetcher.py` + `core/fundamentals.py` point-in-time
  store). SEC XBRL carries each value's `filed` date — the public-availability stamp nothing else gives for
  free. `submissions` carries the SIC code (classification / comparables). Key rules:
  - place every value on its **`filed`** date, never the period it describes;
  - take **as-first-filed** (earliest `filed` per period+concept) to ignore later restatements;
  - the **`frames`** API returns one concept across *all* filers per quarter — universe-scale without 500 calls;
  - concept normalization (`EarningsPerShareDiluted` vs `…Basic`, mis-tags) is the real build cost.
- **yfinance fundamentals are deliberately not used.** A second source would let the screener and the
  backtester silently disagree. Screen and backtest must read identical numbers.

### Universe (`core/universe.py`)

Start with **today's S&P 500**, read from a committed `data/sp500.csv` (paste the constituents table — a
`Symbol` column, optionally `GICS Sector` / `GICS Sub-Industry`). A committed file is fully deterministic — no
live scrape — so a backtest re-derives identically. `members` is all-`True`, so every artifact is stamped
*"survivorship-biased — indicative."* This is honest because it's labeled, and it unblocks all the machinery.
The upgrade — real historical membership plus delisting / last-price liquidation — fills the same `members`
mask later, again with no strategy changes. `ListUniverse` wraps an explicit `--tickers` list the same way.

### Engine — keep `bt`, swappable

`bt` expresses target-weight rebalancing directly and handles 500 names over 20 years for a single config in
seconds. Correctness outranks speed, and the bias work is engine-agnostic. The engine stays behind
`engine/runner.py`; `vectorbt` gets revisited only when *parameter sweeps* (hundreds of configs) actually
bottleneck — not before.

### Screener = the strategy's latest row

A screener is not separate code. `strategy.weights(ctx).iloc[-1]` filtered to nonzero **is** today's book:

```python
book = LongShortPE().weights(ctx).iloc[-1]   # scan the universe right now
book[book != 0]                               # the longs (+) and shorts (−) to hold today
```

Backtest = run `weights(ctx)` over all history. Screen = read its last row. Paper-trade = send that row to the
broker (the existing `paper_trade.py` path). Research, backtest, and live can never drift, because they are the
same function on the same data.

### Research bed (`research/`)

- **Universe sweep (built — `research/sweep.py`, `research/report.py`).** `sweep_universe(strategy, universe,
  benchmark, …)` runs a **single-asset** rule independently on every name in a universe and returns a per-name
  metrics frame (alpha / beta / Sharpe / return), with `quantstats` owning the metrics. The report
  (`write_distribution_report`) writes per-name CSVs and an interactive **alpha-vs-beta scatter with marginal
  histograms** — so momentum is judged on its *distribution across the market* (what fraction beat the
  benchmark), not on one cherry-picked ticker. The `sweep.py` CLI drives it; every artifact carries the
  universe's bias stamp.
- **Strategy comparison (planned).** `compare(specs, ctx, benchmark)` — run N strategies / param sets against
  one universe in a single `bt.run(*tests)` and emit a combined metrics table + overlaid equity explorer. For a
  long/short book the headline diagnostic is **beta ≈ 0** (market-neutrality), which `quantstats` already
  provides. Closes the open "Portfolio comparison view" from `docs/00-direction.md`.

### What's new vs reused

| New | Reuse (bends to fit) |
|-----|----------------------|
| `core/context.py` — `DataContext` | `core/data_loader.py` cache (EDGAR = new data-kind in the MD5 key) |
| `core/universe.py` — S&P 500 membership | `core/price_panel.py` — one panel inside the context |
| `data_ingestion/edgar_fetcher.py` + `core/fundamentals.py` — PIT store | `strategies/` registry; `xs_momentum` is already cross-sectional |
| `research/lab.py` + `research/report.py` | `engine/runner.py`, `engine/frequency.py`, `guardrails/`; `reporting/`; `brokers/`, `paper_trade.py` |

The platform is ~three real new modules (context, universe, EDGAR PIT store) plus a research bed. Everything
else already exists and adapts. Feasibility is high: 500 names × 20y daily is ~2.5M cells (trivial in pandas),
and EDGAR `frames` pulls a whole concept across all filers per quarter.

## Roadmap

- **A — Interface migration (behavior-preserving). [done]** `DataContext` + pluggable `core/sources.py`;
  strategies migrated to `weights(ctx)`; price-only context (`members` all-`True`). All tests green.
- **B — Universe + research bed (price only). [partly done]** `core/universe.py` (labeled-biased S&P 500 from
  `data/sp500.csv`) + the single-asset **universe sweep** with the alpha/beta distribution report ship the
  Home-Depot selection-bias fix for `momentum`. Still to do: the multi-strategy `compare`/param-sweep and
  CAPM rolling beta as a derived feature.
- **C — EDGAR point-in-time fundamentals. [v1 done]** `data_ingestion/edgar_fetcher.py` (CIK map + cached
  companyconcept) + `core/fundamentals.py` (annual diluted EPS, **as-first-filed**, exposed as the `eps`
  panel); strategies declare `requires=("eps",)`; `build_context` forward-fills it point-in-time onto the
  calendar; the dollar-neutral `ls_pe` long/short ships with an as-first-filed + PIT no-look-ahead test. First
  trustworthy fundamental backtest. Next EDGAR steps: **TTM** EPS (vs annual), market-cap (shares × price) and
  SIC for the volatility/comparables screens.
- **D — Survivorship upgrade.** Historical membership into `members` + delisting / last-price handling. Removes
  the labeled bias through the same pipeline.
- **E — Risk / volatility layer.** With metrics finally trustworthy: volatility targeting, position caps, more
  guardrails — the stated end-state ("cancel the biases, *then* focus on volatility").
- *(Later)* `vectorbt` if sweeps demand it; news / sentiment behind the same point-in-time seam.

## Residual biases to keep labeled

Even done right, every report must stamp what it still can't promise:

- **Survivorship** — until Phase D, the universe is today's members; losers that were delisted are missing.
- **Short-borrow & turnover costs** — `bt` shorts/rebalances are frictionless; real L/S returns are optimistic.
- **Sample / regime** — one backtest window is one regime; out-of-sample discipline still applies (see
  `AGENT.md` non-negotiable 6).
