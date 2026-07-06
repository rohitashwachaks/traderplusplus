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

The pipeline runs end-to-end: **data → `DataContext` → strategy weights → `bt` → reports**, universe-first and
point-in-time. See `docs/03-research-platform.md` for the design.

- `core/sources.py` + `core/context.py` — a `PanelSource` registry (price now, EDGAR `eps` too) behind a
  single `DataContext` (`ctx.price`, `ctx.members`, `ctx.meta`, `ctx.fundamental(name)`). `build_context`
  outer-joins the universe (staggered listings kept as NaN), sets `members = membership & price.notna()`, and
  forward-fills fundamentals from their filing date — point-in-time, no look-ahead.
- `core/universe.py` — the tradable set: `SP500` (from `data/sp500.csv`, labeled survivorship-biased) and
  `ListUniverse` for explicit tickers, each with a membership mask.
- `core/fundamentals.py` + `data_ingestion/edgar_fetcher.py` — SEC EDGAR annual diluted EPS, **as-first-filed**,
  exposed as the `eps` panel (the first point-in-time fundamental).
- `strategies/` — `TargetWeightStrategy` interface + registry (`base.py`), reading a `DataContext` via
  `weights(ctx)`: `buy_n_hold`, `momentum` (single-asset SMA crossover, swept across a universe),
  `xs_momentum` (cross-sectional, monthly), `dual_momentum` (short-vs-long *rate*), and `ls_pe` (dollar-neutral
  long/short on point-in-time P/E, `requires=("eps",)`). All apply a one-bar `.shift(1)`; each carries a
  `rebalance_freq`/`reconstitution_freq` (see `engine/frequency.py`).
- `research/` — `sweep.py` runs a single-asset rule independently across a universe; `report.py` writes the
  alpha/beta **distribution** (per-name CSV + interactive chart) — the antidote to single-ticker selection bias.
- `guardrails/` — `Guardrail` interface + registry (`base.py`); `stop_loss.py` is a configurable
  trailing/fixed stop that overlays the weights (daily close-to-close, no look-ahead, exits to cash).
- `engine/runner.py` — applies guardrails, reconstitution sampling and the rebalance Run-algo to the strategy
  weights, then builds `bt.Strategy([Run<freq>, SelectAll, WeighTarget, Rebalance])` plus a buy-and-hold
  benchmark; returns the combined `bt` result.
- `reporting/` — `report.py` writes CSVs (equity curve, daily returns, `bt` stats, quantstats metrics), PNGs,
  and a quantstats tearsheet; `interactive.py` writes a plotly equity explorer (underlying prices, buy/sell
  markers, per-day portfolio split on hover). Flat/all-cash curves skip the regression metrics with a warning.
- `core/store.py` — the **canonical price store**: one additive parquet series per ticker + a coverage index;
  `ensure()` fetches only the gap between what's stored and what a run needs. Re-running downloads nothing;
  daily prices are served from here (the MD5 request cache remains for intraday only).
- **Trust rails** — `reporting/manifest.py` writes a `manifest.json` (git SHA, args, universe fingerprint,
  bias stamps) into every output dir; every CSV/HTML artifact carries its bias stamps; a golden-file test pins
  a backtest's equity curve against silent drift; CI runs the suite on push.
- **Costs** — `--cost-bps` charges commission+slippage per trade through `bt`'s commissions hook; turnover is
  reported. The default `0` is a deliberate decision (small book, liquid large/mid caps) and is **stamped**
  "frictionless" rather than hidden.
- `engine/journal.py` + `paper_trade.py --reconcile` — every paper plan/execution appends to an append-only
  journal; reconciliation diffs the broker's fills against the plan (slippage in bps, missing/unplanned
  flagged). Ops guide (launchd scheduling, no server): `docs/05-paper-trading.md`.
- `run.py` — CLI: `python run.py --strategy=momentum --tickers=AAPL --benchmark=SPY --start=… --end=…`.
- `tests/` — no-look-ahead, golden-file, store, costs, EDGAR point-in-time, journal/reconcile, smoke — all
  network-free.

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

The step-by-step execution plan — milestones with exit criteria and gap analysis — lives in
`docs/01-roadmap.md`. The coarse phases:

- [x] **0. Lock the baseline.** Captured the old engine's behaviour before replacing it.
- [x] **1. Engine spike.** `bt` stood up on `buy_n_hold`/`momentum` fed by the existing data layer, with reports.
- [~] **2. Strategy + research platform.** `xs_momentum` delivers the real multi-ticker, cross-sectional,
      periodically-reconstituted strategy. The rest of this phase is now the **universe-first, point-in-time
      research platform** (`docs/03-research-platform.md`, phases A–E): the `weights(ctx)` migration, a
      labeled-biased S&P 500 universe, EDGAR point-in-time fundamentals, and the research/compare-sweep bed
      (which subsumes the old "Portfolio comparison view").
- [~] **3. Trust, tests & risk.** No-look-ahead + smoke tests, stop-loss guardrail, **golden-file
      reproducibility test, CI, run manifests + bias-stamped artifacts, trading-cost hook** — all in. Still
      to do: more guardrails (max-drawdown, position caps, vol targeting — roadmap M5).
- [~] **4. Automated paper trading.** `paper_trade.py` recomputes the current target weights (same strategy/
      guardrail/frequency config), diffs them against live Alpaca **paper** positions via a thin broker port
      (`brokers/`), previews or executes, **journals every plan, and reconciles fills against the plan**
      (`--reconcile`, slippage in bps). Scheduling is documented (launchd — `docs/05-paper-trading.md`).
      Still to do: drift monitor (paper equity vs backtest expectation) + alerting.
- [ ] **5. Live paper / hardening.** Promote to live paper; add monitoring, alerting, failure handling.

## Immediate next steps

Driven by `docs/01-roadmap.md` (milestones): the **M2 compare bed** (multi-strategy comparison — currently
held, design sketched in the roadmap), the **M4 survivorship decision spike** (pick the delisted-inclusive
data source; membership must be true point-in-time — a name selected one quarter and dropped at the next
reconstitution has to enter and leave `ctx.members` on those dates), and the **M5 risk layer** (more
guardrails, now trivially attachable per strategy). The universe also generalizes beyond equities: commodities
/ gold / oil exposure via exchange-traded products under the same membership seam (see roadmap M4 note).

## Feasibility

High. The hardest-to-get-right parts (data ingestion + caching) already work and are library-agnostic. Adopting
`bt` *reduced* surface area. The daily horizon keeps paper trading simple — "recompute weights on a schedule,
diff holdings, send orders" — no live-parity engine required.
