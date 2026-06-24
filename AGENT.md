# Trader++ — Agent Guide

Operating manual for any AI agent (Claude Code, Codex, etc.) working in this repo.
Read this before editing. It encodes what we're building and the bar every change must clear.

## What this is

A **trustworthy personal research backtester**, evolving toward automated paper trading.
The animating principle, from the README, is *"a tool that doesn't lie to me."* Correctness is the
product. A backtest that is fast, pretty, and subtly wrong is worse than useless — it loses real money.

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
core/data_loader.py  parquet cache (MD5 key per ticker/range/interval/source) — KEEP
core/price_panel.py  OHLCV dict → tz-naive close panel for bt
strategies/          base.py (TargetWeightStrategy + registry), buy_n_hold.py, momentum.py
engine/runner.py     builds & runs the bt backtest (+ benchmark)
reporting/report.py  CSVs, PNGs, quantstats tearsheet
run.py               CLI entry point
tests/               no-look-ahead + smoke (network-free)
```

## Working in this repo

- **Env:** conda env `options-trading`. The `conda` function is broken here, so call the interpreter by path:
  `/Users/rchaks/opt/miniforge3/envs/options-trading/bin/python`.
- **Run a backtest:**
  `…/python run.py --strategy=momentum --tickers=AAPL --benchmark=SPY --start=2023-01-01 --end=2024-01-01`
- **Tests:** `…/python -m pytest tests/ -q`.
- **Secrets:** `.env` (gitignored) holds API keys; read via `utils/config.py`. Never commit or print keys.
  Add new config there, not scattered `os.getenv` calls.
- **Tests are the credibility gate.** Every new strategy ships with a no-look-ahead test. Don't add one without.
- **Scope discipline.** Don't rebuild what `bt`/`ffn`/`quantstats` already provide. Don't add live-trading or
  derivatives code until its phase. Smaller, correct, reviewed beats broad and unverified.
