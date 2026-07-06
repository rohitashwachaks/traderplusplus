# Trader++ — Agent Guide

Operating manual for any AI agent (Claude Code, Codex, etc.) working in this repo.
Read this before editing. It encodes what we're building and the bar every change must clear.

## What this is

A **trustworthy personal research backtester**, evolving toward automated paper trading.
The animating principle, from the README, is *"a tool that doesn't lie to me."* Correctness is the
product. A backtest that is fast, pretty, and subtly wrong is worse than useless — it loses real money.

This is a **personal instrument, not a product**: no customers, no monetization, no feature-parity
chasing. Decisions optimize for the owner's trust in his own results.

Constraints that shape every decision:

- **Horizon:** no intraday/HFT. Positions held ~1 day to 6 months → **daily bars** are the unit of time.
- **Style:** **rebalancing / reconstitution** strategies — *signal/score → target weights → rebalance*.
  Future signals may come from screeners and AI-agent / news sources, so strategies express **target
  weights**, not hand-rolled order quantities.
- **Portfolio = a reporting / comparison view.** Run several strategies side by side, compare
  alpha/beta/Sharpe/drawdown/risk, and watch overall-portfolio risk. It is **not** a second accounting system.
- **Trajectory:** research backtest → automated paper trading → live paper trading. Broker stays behind a
  thin, swappable interface (Alpaca paper first; IBKR a later swap).

## Architecture (live)

The hand-rolled engine is gone. The pipeline is **data → price panel → strategy weights → `bt` → reports**:

- **Engine:** [`bt`](https://pmorissette.github.io/bt/) — rebalancing-first; `WeighTarget` consumes a strategy's
  target-weight DataFrame.
- **Metrics:** `ffn` + `quantstats` — do **not** hand-maintain Sharpe/alpha/beta/drawdown.
- **Data layer (kept):** `data_ingestion/*` + `core/data_loader.py` parquet cache — library-agnostic.
- **Out of scope (deleted):** derivatives, live trading — they return in their roadmap phase, not before.

**Direction (in progress):** the platform is moving to **universe-first, point-in-time** research
(`docs/03-research-platform.md`). The strategy input migrates from `weights(prices)` to **`weights(ctx)`** (a
`DataContext` of price · membership · classification · point-in-time fundamentals); **EDGAR is the single
fundamentals/SIC source** (one source of truth — no yfinance fundamentals); the universe starts labeled
survivorship-biased and upgrades through the same seam. `bt` stays the engine, swappable behind `engine/runner`.

Full reasoning, current state, and the roadmap live in `docs/00-direction.md`. When in doubt about scope or
direction, that doc wins.

## Non-negotiables (this is critical infrastructure)

1. **No look-ahead bias. Ever.** A signal for day *t* may only use data through day *t*.
   - Compute indicators on data sliced to `<= current_date`; never index future rows.
   - No `.shift(-n)`, no `.iloc[i+1]`, no full-series fits used to label past bars.
   - With `bt`: weights set from data at *t* execute on the *next* bar — respect that lag, don't defeat it.
   - Every new strategy needs a test that would fail if it peeked. No exceptions.
2. **No silent failures.** Never wrap logic in a bare `except Exception: ... continue/pass`. If something
   can't be computed, **raise** with a clear message, or skip explicitly with a logged, narrow condition.
   A backtest that swallows an error and returns a flat curve is the cardinal sin here.
3. **Accounting must reconcile.** Cash + holdings value must be conserved across every transaction.
   Position changes and cash changes are two sides of one entry — never update one without the other.
4. **Deterministic & reproducible.** Same inputs → same output. Seed anything stochastic. Pin the date
   range and data source so a result can be re-derived.
5. **Correctness over cleverness.** Prefer the boring, obviously-correct implementation. If a clever
   vectorized trick risks look-ahead or obscures intent, don't.
6. **A backtest must be valid as an *experiment*, not just as code.** Line-level no-look-ahead (#1) is
   necessary, not sufficient. Before trusting a result, account for the biases that make a clean-running
   backtest still a lie:
   - **Selection bias** — a hand-picked ticker is a cherry-pick; validate rules *cross-sectionally over the
     whole universe*, never on one name you already know won.
   - **Survivorship bias** — test over the universe *as it existed then* (delisted names included), not today's
     survivors.
   - **Point-in-time data** — fundamentals / alt-data keyed to when they became *public* (filing date),
     as-first-filed, never the period they describe or a later restatement.
   - **Overfitting / data-snooping** — params tuned on the test window prove nothing; keep out-of-sample
     discipline and prefer few, defensible knobs.
   - **Costs & frictions** — frictionless shorts / turnover flatter returns; name what isn't modeled.

   Every report must **stamp the biases it still carries**. A labeled-approximate backtest is honest; an
   unlabeled one is the cardinal sin. The platform that operationalizes this is `docs/03-research-platform.md`.

## Code hygiene — every line must earn its place

You are penalized for every useless line. Write the minimum code that is correct and clear.

- **Delete, don't comment out.** Dead/commented-out code is forbidden. Git is the history.
- **No debug residue.** No stray `print('here')`, no leftover scratch. Use the logger for real diagnostics.
- **Small, single-purpose functions.** If a function needs a paragraph to explain, split it.
- **Type everything** — match existing style: Python 3.10+ unions (`pd.DataFrame | None`), `typing`
  imports, explicit return types on public methods.
- **Validate at the boundary.** Follow the existing `assert`-with-message pattern in constructors for
  precondition checks; raise `ValueError` for runtime/business errors.
- **Docstrings: Google style, and only when they add information.** Document *why* and non-obvious
  contracts (especially look-ahead guarantees, units, side effects). Don't restate the signature or write
  empty `:param x:` stubs — the repo has these; don't add more.
- **Names say what they mean.** Match the domain vocabulary in use (weights, rebalance, panel, signal,
  benchmark). No abbreviations that aren't already idiomatic here.
- **One source of truth.** Don't duplicate logic or state. Let `bt` own accounting and `ffn`/`quantstats`
  own metrics; a "Portfolio" is a *reporting view*, never a parallel ledger.
- **Reuse before adding.** Check `utils/`, `core/`, and the data layer before writing new helpers.

## Anti-patterns to fix on sight

- Bare `except` that hides failures → raise, or narrow + log.
- Single-ticker hardcoding (e.g. `list(positions.keys())[0]`) in portfolio strategies → support multi-asset.
- Commented-out code blocks → delete.
- Hand-rolled metrics that duplicate `ffn`/`quantstats` → replace.
- Any new accounting path that competes with `bt` → fold into the reporting view.

## Layout

```text
data_ingestion/      provider fetchers (yahoo, polygon, alpaca) — KEEP
core/store.py        canonical price store: additive per-ticker parquet + coverage.json, gap-only fetching (daily bars)
core/data_loader.py  legacy request cache (MD5 key) — intraday only; daily prices go through the store
core/price_panel.py  OHLCV dict → tz-naive close panel for bt (+ data-quality gate: dupes raise, bad prices nulled loudly)
core/sources.py      PanelSource registry (price, eps, eps_ttm, shares) — pluggable data behind the context
core/context.py      DataContext: price · members · meta · fundamental(name) — the single strategy input; build_context outer-joins + ffills feature panels (point-in-time)
core/universe.py     Universe (ListUniverse, SP500 from data/sp500.csv) + membership mask + fingerprint (for manifests)
core/fundamentals.py PIT panels, all as-first-filed & filed-date keyed: annual EPS · TTM EPS (Q4 from the 10-K) · shares (mcap = price × shares) · sic_meta
data_ingestion/edgar_fetcher.py  SEC EDGAR: ticker→CIK (SEC map + committed-CSV overlay), companyconcept, companyfacts (full 10-K/10-Q line items), submissions (SIC)
data/sp500.csv       pasted S&P 500 constituents incl. CIK — committed input
strategies/          base.py (TargetWeightStrategy + registry, freq, single_asset, requires, attachable guardrails), buy_n_hold.py, momentum.py (single-asset), cross_sectional_momentum.py (xs_momentum), dual_window_momentum.py (dual_momentum), long_short_pe.py (ls_pe, requires eps)
guardrails/          base.py (Guardrail + registry), stop_loss.py — risk overlays on weights
research/            sweep.py (single-asset rule across a universe → per-name alpha/beta), report.py (distribution chart)
engine/runner.py     builds & runs the bt backtest (+ benchmark), applies guardrails + frequencies + cost_bps commissions
engine/frequency.py  rebalance Run-algo + reconstitution resampling + RunOnDays/AnyOf (guardrail exits trade immediately)
engine/paper.py      rebalance plan (diff targets vs positions → orders) + fill reconciliation (slippage in bps)
engine/journal.py    append-only JSONL journal of every paper plan / execution / reconciliation
reporting/report.py  bias-stamped CSVs (+ turnover), PNGs, quantstats tearsheet
reporting/interactive.py  plotly equity explorer (holdings split on hover, buy/sell markers, caveat in title)
reporting/manifest.py  manifest.json per output dir: git SHA, args, universe fingerprint, bias stamps
brokers/             base.py (Broker port incl. order history), alpaca.py (paper, REST via requests)
run.py               backtest CLI entry point (--tickers or --universe; single-asset strategies redirect to sweep)
sweep.py             universe-sweep CLI: run a single-asset strategy on every name → alpha/beta distribution
paper_trade.py       paper-rebalance CLI (preview by default; --execute to submit; --reconcile to audit fills)
tests/               no-look-ahead + golden-file + store + costs + EDGAR PIT + journal/reconcile + smoke (network-free)
```

Strategies receive a `DataContext` (`weights(ctx)`), never a raw price frame, and only hold names where
`ctx.members` is true. A strategy declares any non-price data it needs via `requires` (e.g. `ls_pe` sets
`requires = ("eps",)`); `build_context` loads those panels and forward-fills them point-in-time onto the
trading calendar. A *single-asset* strategy (e.g. `momentum`) is validated by **sweeping** it across a universe
one name at a time and reading the distribution of alpha/beta — not by pooling names into a basket.

Point-in-time fundamentals come **only** from SEC EDGAR (each value keyed to its `filed` date,
as-first-filed): annual EPS, TTM EPS, shares outstanding (→ market cap), SIC, and the full 10-K/10-Q
line-item history via `fetch_company_facts` — the seam new fundamental panels are built from.

## Working in this repo

- **Env:** conda env `options-trading`. The `conda` function is broken here, so call the interpreter by path:
  `/Users/rchaks/opt/miniforge3/envs/options-trading/bin/python`.
- **Run a backtest:**
  `…/python run.py --strategy=momentum --tickers=AAPL --benchmark=SPY --start=2023-01-01 --end=2024-01-01`
- **Sweep a single-asset rule across a universe** (the honest, selection-bias-free way to judge momentum):
  `…/python sweep.py --strategy=momentum --universe=sp500 --benchmark=SPY --start=2019-01-01 --end=2024-01-01`
  (paste S&P 500 members into `data/sp500.csv`; `--limit N` for quick runs).
- **Tests:** `…/python -m pytest tests/ -q`.
- **Secrets:** `.env` (gitignored) holds API keys; read via `utils/config.py`. Never commit or print keys.
  Add new config there, not scattered `os.getenv` calls.
- **Tests are the credibility gate.** Every new strategy ships with a no-look-ahead test. Don't add one without.
- **Scope discipline.** Don't rebuild what `bt`/`ffn`/`quantstats` already provide. Don't add live-trading or
  derivatives code until its phase. Smaller, correct, reviewed beats broad and unverified.
