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

## Architectural direction (in progress)

We are **retiring the hand-rolled backtest engine** (`core/backtester.py`, `core/market_data.py`,
`executors/backtest.py`) and standing on proven libraries:

- **Engine:** [`bt`](https://pmorissette.github.io/bt/) — rebalancing-first, composable `Algo`s, multi-asset.
- **Metrics:** `ffn` + `quantstats` — do **not** hand-maintain Sharpe/alpha/beta/drawdown.
- **Keep:** the data layer (`data_ingestion/*`, `core/data_loader.py` parquet cache) — it's the most
  reusable asset and is library-agnostic.
- **Drop:** `strategies/derivatives/*` (out of scope).

Full reasoning and the migration roadmap live in `docs/00-direction.md`. When in doubt about scope or
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

- **Delete, don't comment out.** Dead/commented-out code is forbidden (the repo currently has some — e.g.
  the commented `StrategyFactory.__init__` in `strategies/base.py`; remove such blocks when you touch them).
  Git is the history.
- **No debug residue.** No stray `print('here')`, no leftover scratch. Use the logger for real diagnostics.
- **Small, single-purpose functions.** If a function needs a paragraph to explain, split it.
- **Type everything** — match existing style: Python 3.10+ unions (`pd.DataFrame | None`), `typing`
  imports, explicit return types on public methods.
- **Validate at the boundary.** Follow the existing `assert`-with-message pattern in constructors for
  precondition checks; raise `ValueError` for runtime/business errors.
- **Docstrings: Google style, and only when they add information.** Document *why* and non-obvious
  contracts (especially look-ahead guarantees, units, side effects). Don't restate the signature or write
  empty `:param x:` stubs — the repo has these; don't add more.
- **Names say what they mean.** Match domain vocabulary already in `contracts/` (Asset, Order, Portfolio,
  weights, rebalance). No abbreviations that aren't already idiomatic here.
- **One source of truth.** Don't duplicate logic or state. If two places compute net worth or metrics,
  collapse them. (This is why Portfolio is a *view*, not a parallel ledger.)
- **Reuse before adding.** Check `utils/`, `contracts/`, and the data layer before writing new helpers.

## Anti-patterns to fix on sight

- Bare `except` that hides failures (`core/backtester.py` loop) → raise or narrow + log.
- Single-ticker hardcoding `list(positions.keys())[0]` in "portfolio" strategies → support multi-asset.
- Commented-out code blocks → delete.
- Hand-rolled metrics that duplicate `ffn`/`quantstats` → replace.
- Any new accounting path that competes with the chosen engine's → fold into the reporting view.

## Layout

```text
data_ingestion/   provider fetchers (yahoo, polygon, alpaca) — KEEP
core/data_loader  parquet cache (MD5 key per ticker/range/interval/source) — KEEP
contracts/        domain types: Portfolio (→ reporting view), Asset, Order, TradeLog
strategies/       authoring layer → reshape around target weights; single_asset/, multi_asset/
analytics/        being replaced by ffn/quantstats
core/backtester   being replaced by bt
```

## Working in this repo

- **Run a current backtest (baseline reference):**
  `python run_backtest.py --strategy=momentum --tickers=AAPL --start=2023-01-01 --end=2024-01-01`
- **Secrets:** `.env` (gitignored) holds API keys; read via `utils/config.py`. Never commit keys; never
  print them. Add new config there, not scattered `os.getenv` calls.
- **Tests are the credibility gate.** New strategy/accounting logic ships with tests — at minimum a
  golden-file expectation and a no-look-ahead check. Don't add a strategy without one.
- **Scope discipline.** Don't rebuild what `bt`/`ffn`/`quantstats` already provide. Don't add live-trading
  or derivatives code until its phase. Smaller, correct, reviewed beats broad and unverified.
