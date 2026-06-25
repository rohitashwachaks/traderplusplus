# Direction & Roadmap

Why this project is shaped the way it is, and where it's going. For day-to-day coding rules see `AGENT.md`.

## North star

A **trustworthy personal research backtester**, evolving toward automated paper trading. The product *is*
correctness — *"a tool that doesn't lie to me."* A fast, pretty, subtly-wrong backtest loses real money.

Constraints that drive every decision:

- **Horizon:** no intraday/HFT. Holds ~1 day to 6 months → **daily bars**.
- **Style:** rebalancing / reconstitution — *signal/score → target weights → rebalance*. Future signals may
  come from screeners and AI-agent / news sources, so strategies express **target weights**, not raw orders.
- **Unit of test:** a *rule over a point-in-time universe*, not a strategy over a hand-picked ticker. A single
  name is the degenerate N=1 case. See `docs/03-research-platform.md`.
- **Portfolio = reporting / comparison view:** compare strategies' alpha/beta/Sharpe/drawdown/risk and track
  overall-portfolio risk. Not a second accounting system.
- **Trajectory:** research backtest → automated paper trading → live paper trading. Broker behind a thin,
  swappable interface (Alpaca paper first; IBKR a later swap).

## The pivot (done): proven engine instead of a hand-rolled loop

We **retired the hand-rolled backtest engine** and stand on proven libraries. Settled stack, now live:

- **Engine:** [`bt`](https://pmorissette.github.io/bt/) — rebalancing-first, composable `Algo`s, multi-asset,
  free. `WeighTarget` turns any score (screener / AI / news) into target weights.
- **Metrics:** `ffn` + `quantstats` — no hand-maintained Sharpe/alpha/beta/drawdown.
- **Data layer (kept):** `data_ingestion/*` fetchers + `core/data_loader.py` parquet cache — library-agnostic.
- `vectorbt` is held in reserve for heavy parameter-sweep research; event-driven engines (backtrader /
  nautilus) stay deprioritized — they solve a latency problem we don't have.

## Current state

The pipeline runs end-to-end: **data → price panel → strategy weights → `bt` → reports**.

- `core/price_panel.py` — adapts the per-ticker OHLCV dict into a tz-naive close-price panel for `bt`.
- `strategies/` — `TargetWeightStrategy` interface + registry (`base.py`), with `buy_n_hold`, `momentum`
  (single-name SMA crossover) and `xs_momentum` (cross-sectional: rank a basket, hold the top names
  equal-weighted, reconstituted monthly). All apply a one-bar `.shift(1)` so signals never look ahead. Each
  strategy carries a `rebalance_freq` and `reconstitution_freq` (default daily) — see `engine/frequency.py`.
- `guardrails/` — `Guardrail` interface + registry (`base.py`); `stop_loss.py` is a configurable
  trailing/fixed stop that overlays the weights (daily close-to-close, no look-ahead, exits to cash).
- `engine/runner.py` — applies guardrails, reconstitution sampling and the rebalance Run-algo to the strategy
  weights, then builds `bt.Strategy([Run<freq>, SelectAll, WeighTarget, Rebalance])` plus a buy-and-hold
  benchmark; returns the combined `bt` result.
- `reporting/` — `report.py` writes CSVs (equity curve, daily returns, `bt` stats, quantstats metrics), PNGs,
  and a quantstats tearsheet; `interactive.py` writes a plotly equity explorer (underlying prices, buy/sell
  markers, per-day portfolio split on hover). Flat/all-cash curves skip the regression metrics with a warning.
- `run.py` — CLI: `python run.py --strategy=momentum --tickers=AAPL --benchmark=SPY --start=… --end=…`.
- `tests/` — a no-look-ahead test (truncating the future can't change a past weight) and an end-to-end smoke
  test. Both network-free.

The **entire legacy engine cluster was deleted** (old CLIs, `core/backtester.py`, `market_data.py`,
`visualizer.py`, `executors/`, `analytics/`, `contracts/`, `guardrails/`, `brokers/`, old `strategies/*`,
`utils/metrics.py`). `contracts`/`guardrails`/broker will return as clean, purpose-built modules in their
phases below — not as carried-over dead code.

**Environment:** conda env `options-trading` (pandas ≥ 2.2, `bt`, `quantstats`). The `conda` shell function is
broken on this machine; invoke the interpreter by absolute path
(`/Users/rchaks/opt/miniforge3/envs/options-trading/bin/python`).

## The bias reckoning (why no-look-ahead isn't enough)

The engine's `shift(1)` / truncation discipline guards exactly **one** bias — temporal leakage in a price
signal — and that rigor quietly created a false sense of safety. Three deeper biases went unchallenged and now
shape the platform's direction:

- **Selection bias** — backtesting a hand-picked surviving ticker (momentum on AAPL / Home Depot) proves
  nothing; the *choice of ticker* is the cheat. Validate rules cross-sectionally over a whole universe.
- **Survivorship bias** — backtesting the past on *today's* index members deletes the delisted losers.
- **Point-in-time fundamentals** — a P/E strategy needs the P/E that was *public* on each past date (filing
  date), not today's snapshot.

The fix is the **universe-first, point-in-time research platform** in `docs/03-research-platform.md`: a
`DataContext` keystone, EDGAR as the single point-in-time fundamentals/SIC source, a (initially labeled
survivorship-biased) universe, and bias-stamped reports. The methodology rule this taught is now `AGENT.md`
non-negotiable 6 ("a backtest must be valid as an experiment, not just as code").

## Roadmap

- [x] **0. Lock the baseline.** Captured the old engine's behaviour before replacing it.
- [x] **1. Engine spike.** `bt` stood up on `buy_n_hold`/`momentum` fed by the existing data layer, with reports.
- [~] **2. Strategy + research platform.** `xs_momentum` delivers the real multi-ticker, cross-sectional,
      periodically-reconstituted strategy. The rest of this phase is now the **universe-first, point-in-time
      research platform** (`docs/03-research-platform.md`, phases A–E): the `weights(ctx)` migration, a
      labeled-biased S&P 500 universe, EDGAR point-in-time fundamentals, and the research/compare-sweep bed
      (which subsumes the old "Portfolio comparison view").
- [~] **3. Trust, tests & risk.** No-look-ahead + smoke tests exist; a configurable stop-loss guardrail
      (trailing/fixed) is in and tested. Still to do: return-reproducibility/golden files, more guardrails
      (max-drawdown, position caps), and CI.
- [~] **4. Automated paper trading.** `paper_trade.py` recomputes the current target weights (same strategy/
      guardrail/frequency config), diffs them against live Alpaca **paper** positions via a thin broker port
      (`brokers/`), and previews the orders; `--execute` submits them. Still to do: scheduling, fill
      reconciliation against backtest expectations.
- [ ] **5. Live paper / hardening.** Promote to live paper; add monitoring, alerting, failure handling.

## Immediate next steps

Driven by `docs/03-research-platform.md` (phase letters below):

1. **Phase A — `weights(ctx)` migration.** Introduce the `DataContext` keystone and migrate the existing
   strategies onto it (price-only context, `members` all-`True`). Behavior-preserving; existing tests stay green.
2. **Phase B — universe + research bed (price only).** Labeled-biased S&P 500 universe so momentum / xs_momentum
   are tested cross-sectionally (the selection-bias fix), plus the compare/sweep research bed with bias-stamped
   reports (subsumes the old "Portfolio comparison view").
3. **Phase C — EDGAR point-in-time fundamentals.** The PIT store + `ctx.fundamental("pe")` + the `ls_pe`
   long/short strategy + a fundamentals no-look-ahead test — the first trustworthy fundamental backtest.

## Feasibility

High. The hardest-to-get-right parts (data ingestion + caching) already work and are library-agnostic. Adopting
`bt` *reduced* surface area. The daily horizon keeps paper trading simple — "recompute weights on a schedule,
diff holdings, send orders" — no live-parity engine required.
