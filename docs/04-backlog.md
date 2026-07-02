# Backlog, Ideas & Open Decisions

A living record of what's planned, what's worth exploring, decisions to revisit, and known limitations. This is
the place to park an idea so we can pick it up later. For *committed* direction and the phased roadmap, see
[`00-direction.md`](./00-direction.md) and [`03-research-platform.md`](./03-research-platform.md).

> Convention: `[P0]` next up · `[P1]` soon · `[P2]` someday. Move items into the roadmap when they're committed.

---

## 1. Planned features (committed direction)

### Research platform
- **[P0] Multi-strategy comparison view** — `research/compare(specs, ctx, benchmark)`: run N strategies/params
  in one `bt.run(*tests)`, emit a combined alpha/beta/Sharpe/drawdown table + overlaid equity explorer. Closes
  the old "portfolio comparison view." (Phase B remainder.)
- **[P1] CAPM rolling-beta as a derived feature** (`features/beta.py`) — needs only price + benchmark; feeds
  low-beta / betting-against-beta screens and is a natural diagnostic. Start of a `features/` layer.
- **[P1] TTM EPS** (vs the current annual EPS) — sum the last 4 quarterly diluted EPS each known as-of date.
  Needs the Q4-from-10-K reconstruction (Q4 = annual − Σ(Q1..Q3)); more responsive P/E.
- **[P1] Market cap + SIC from EDGAR** — shares outstanding (`dei:EntityCommonStockSharesOutstanding`) × price
  → market cap; SIC from `submissions`. Unlocks the "5 most volatile of the top-50 by market cap, reconstitute
  annually" screen and sector-neutral books.

### Trust, risk & ops
- **[P0] Survivorship-free universe** (Phase D) — real historical S&P 500 membership into `ctx.members`, plus
  delisting / last-price liquidation. The single biggest remaining honesty gap. Decide source (see §3).
- **[P1] Risk / volatility layer** (Phase E) — volatility targeting, position caps, max-drawdown guardrail.
  Only meaningful once the metrics are bias-corrected.
- **[P1] Return-reproducibility / golden files** — pin a run's outputs so a refactor that changes results is
  caught.
- **[P2] CI** — run `pytest` on push; the test suite is currently the only gate.
- **[P2] Paper-trading scheduling + fill reconciliation** — cron/scheduler around `paper_trade.py`; reconcile
  actual fills against backtest expectations.

---

## 2. Ideas to explore (not committed)

- **Screener as a standalone tool** — expose `strategy.weights(ctx).iloc[-1]` as a "scan the universe right now"
  CLI/notebook view (same logic as the backtest's last row).
- **Derived-features layer** (`features/`) — returns, beta, value/quality z-scores as point-in-time panels that
  strategies compose; keeps raw panels and ratios cleanly separated.
- **More strategies** — mean-reversion, breakout, sector-neutral L/S, betting-against-beta, comparables /
  peer-relative value (using SIC/sector).
- **Multi-asset-class long/short** — the original hypothesis: a small L/S book spanning different asset classes
  on a P/E (or other) signal. Needs cross-asset data + thinking about how "universe" generalizes.
- **`vectorbt`** for heavy parameter sweeps — only when bt sweep speed actually bottlenecks (hundreds+ of
  configs). The data layer is engine-agnostic, so this is a contained swap behind `engine/runner`.
- **News / sentiment alt-data** — behind the same point-in-time `PanelSource` seam (publication date = `filed`
  analog). Noisier, often paid.
- **AI-agent / screener signals** as strategy inputs — score → target weights, same interface.
- **DSL / YAML strategy config** — no-code strategy authoring.
- **Use the `CIK` column already in `data/sp500.csv`** to resolve ticker→CIK for EDGAR instead of the
  `company_tickers.json` map — avoids ticker-mismatch and a network call.

---

## 3. Decisions to make / revisit

- **EPS: annual (now) → TTM?** Annual is unambiguous and point-in-time but stale up to ~15 months; TTM is more
  responsive but needs Q4 reconstruction. Revisit when P/E responsiveness matters.
- **Survivorship universe source** — Wikipedia change-log (free, manual reconstruction) vs Norgate / Sharadar
  (cheap paid, delisted-inclusive, done right). Cost vs effort.
- **`data/sp50.csv`** — a 49-name subset (with a `CIK` column) exists but isn't wired to a universe. Decide:
  add an `sp50` universe? a generic file-path universe (`--universe-file`)? use its CIK column for EDGAR?
- **Transaction costs / borrow / slippage** — `bt` is frictionless; L/S and high-turnover returns are
  optimistic. When (and how) to model commissions, short-borrow, and slippage.
- **Reconstitution vs delisting** — a frozen monthly/quarterly target can hold a name that delists mid-period;
  prices ffill flat (no P&L), so it's harmless but not strictly correct. Accept or tighten.
- **Engine** — stay on `bt` vs adopt `vectorbt`; define the trigger (sweep count / wall-clock).
- **`build_context` default join** — currently `outer` (universe-safe). Confirm this is the right default for
  small explicit `--tickers` lists too.

---

## 4. Known limitations & tech debt

- **Survivorship bias** — `SP500` is *today's* members with an all-`True` mask; labeled on every report, not
  yet fixed (Phase D).
- **Frictionless `bt`** — no commissions / borrow / slippage; long/short and high-turnover results flatter.
- **EDGAR scope** — US filers only; **annual** EPS only; concept normalization is basic (`EarningsPerShareDiluted`
  via a duration filter, no fallback to `…Basic` or tag variants).
- **L/S beta ≠ exactly 0** on small/biased subsets — expected; tighter on the full universe.
- **Sweep cost** — runs one full `bt` backtest per name (N × backtests); fine cached, slow on first 500-name run.
- **`clean_ticker`** (`utils/utils.py`) makes a network call per ticker and rejects dotted / >5-char symbols —
  used only for the benchmark now, but brittle; consider dropping the network validation.
- **`data_ingestion/polygon_fetcher.py`** uses `print()` for retry/rate-limit messages — should use the logger.
- **`data_ingestion/test_alpaca_fetch.py`** — a manual scratch script (not a pytest test); decide keep / move to
  a `scripts/` dir / remove.
- **yfinance `FutureWarning`** (auto_adjust default) — cosmetic; pin the argument explicitly.
- **Code TODOs** — `core/data_loader.py` (dict → multi-indexed frame), `utils/utils.py` (source dispatch).
- **No CI** — tests run locally only.

---

## 5. Done recently (for context)

- Pluggable data layer: `PanelSource` registry + `DataContext`; strategies migrated to `weights(ctx)`.
- Universe-first backtesting: `SP500` from `data/sp500.csv` (labeled biased) + membership mask; outer-join
  basket runner (NaN-safe over staggered histories).
- Universe **sweep** + alpha/beta **distribution** report (selection-bias antidote for single-asset rules).
- SEC EDGAR point-in-time **EPS** (as-first-filed) + the dollar-neutral **`ls_pe`** long/short.
- Strategies: `buy_n_hold`, `momentum`, `xs_momentum`, `dual_momentum`, `ls_pe`.
