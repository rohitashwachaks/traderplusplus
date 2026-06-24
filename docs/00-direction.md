# Direction & Roadmap

Why this project is shaped the way it is, and where it's going. For day-to-day coding rules see `AGENT.md`.

## North star

A **trustworthy personal research backtester**, evolving toward automated paper trading. The product *is*
correctness — *"a tool that doesn't lie to me."* A fast, pretty, subtly-wrong backtest loses real money.

Constraints that drive every decision:

- **Horizon:** no intraday/HFT. Holds ~1 day to 6 months → **daily bars**.
- **Style:** rebalancing / reconstitution — *signal/score → target weights → rebalance*. Future signals may
  come from screeners and AI-agent / news sources, so strategies express **target weights**, not raw orders.
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
- `strategies/` — `TargetWeightStrategy` interface + registry (`base.py`), with `buy_n_hold` and `momentum`
  (the latter applies a one-bar `.shift(1)` so signals never look ahead). Each strategy carries a
  `rebalance_freq` and `reconstitution_freq` (default daily) — see `engine/frequency.py`.
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

## Roadmap

- [x] **0. Lock the baseline.** Captured the old engine's behaviour before replacing it.
- [x] **1. Engine spike.** `bt` stood up on `buy_n_hold`/`momentum` fed by the existing data layer, with reports.
- [ ] **2. Strategy + portfolio layer.** Build the real multi-ticker rebalancing strategy (cross-sectional
      target weights, periodic reconstitution) and the **Portfolio comparison view** that runs several
      strategies and compares their alpha/beta/Sharpe/risk side by side. *(Single-ticker path done; multi-asset
      + comparison view are the next slice.)*
- [~] **3. Trust, tests & risk.** No-look-ahead + smoke tests exist; a configurable stop-loss guardrail
      (trailing/fixed) is in and tested. Still to do: return-reproducibility/golden files, more guardrails
      (max-drawdown, position caps), and CI.
- [~] **4. Automated paper trading.** `paper_trade.py` recomputes the current target weights (same strategy/
      guardrail/frequency config), diffs them against live Alpaca **paper** positions via a thin broker port
      (`brokers/`), and previews the orders; `--execute` submits them. Still to do: scheduling, fill
      reconciliation against backtest expectations.
- [ ] **5. Live paper / hardening.** Promote to live paper; add monitoring, alerting, failure handling.

## Immediate next steps

1. **Multi-ticker rebalancing strategy** — a cross-sectional target-weight strategy (e.g. momentum/volatility
   ranking with periodic reconstitution) to deliver on "portfolio as first-class". `momentum` already supports
   multiple columns; add a strategy that *selects and weights across* tickers.
2. **Portfolio comparison view** — run N strategies in one pass and emit a combined alpha/beta/Sharpe/drawdown
   table (lean on `bt`'s multi-backtest `Result` + quantstats), plus an aggregate-risk readout.
3. **Tighten config** — surface `--cash`, rebalance frequency, and strategy params (e.g. momentum windows)
   through the CLI/strategy constructors.

## Feasibility

High. The hardest-to-get-right parts (data ingestion + caching) already work and are library-agnostic. Adopting
`bt` *reduced* surface area. The daily horizon keeps paper trading simple — "recompute weights on a schedule,
diff holdings, send orders" — no live-parity engine required.
