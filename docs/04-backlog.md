# Backlog, Ideas & Open Decisions

A living record of what's planned, what's worth exploring, decisions to revisit, and known limitations. This is
the place to park an idea so we can pick it up later. For *committed* direction and the phased roadmap, see
[`00-direction.md`](./00-direction.md) and [`01-roadmap.md`](./01-roadmap.md).

> Convention: `[P0]` next up · `[P1]` soon · `[P2]` someday. Move items into the roadmap when they're committed.

---

## 1. Planned features (committed direction)

### Research platform

- **[P0] Multi-strategy comparison view** (roadmap M2 — **held by decision, 2026-07**) —
  `research/compare(specs, ctx, benchmark)`: run N strategies/params in one `bt.run(*tests)`, emit a combined
  alpha/beta/Sharpe/drawdown table + overlaid equity explorer, same stamps/manifest as `run.py`.
- **[P1] CAPM rolling-beta as a derived feature** (`features/beta.py`) — needs only price + benchmark; feeds
  low-beta / betting-against-beta screens and is a natural diagnostic. Start of a `features/` layer.
- **[P1] A proving strategy on the new EDGAR panels** — a market-cap/volatility screen (`shares`, `eps_ttm`),
  with its no-look-ahead test. `sector_neutral_momentum` (2026-07) already exercises SIC/GICS classification;
  a sector-neutral `ls_pe` (rank P/E within `sector`) is the natural next combiner of both.

### Trust, risk & ops

- **[P0] Survivorship-free universe** (roadmap M4) — real point-in-time membership into `ctx.members` (a name
  selected one quarter and dropped at the next reconstitution enters/leaves on those dates), plus delisting /
  last-price liquidation. **Gated on the M4.0 data-source decision** (see §3) — delisted *prices*, not just
  membership, decide it.
- **[P0] Multi-asset (ETP) universe** — oil / gold / commodity / rates exposure via exchange-traded products in
  the same membership seam (roadmap M4 scope note): a composite universe, each component carrying its own
  caveat labels (roll yield / expense drag are part of an ETP's real return; fundamentals panels don't apply).
- **[P1] Risk / volatility layer** (roadmap M5) — vol targeting, position caps, max-drawdown guardrail. The
  authoring seam is ready (strategy-attached `guardrails` tuple, 2026-07); the overlays themselves remain.
- **[P2] Point-in-time classification** — sector/SIC in `ctx.meta` is *static* (today's labels applied to all
  history), a labeled bias that landed with cross-industry strategies (2026-07). Upgrade through the same
  `meta` seam: historical GICS reclassifications / SIC-at-filing (mirrors the survivorship story — the strategy
  never changes, only how meta is built). Sector-neutral books are only mildly sensitive, so this is P2.
- **[P1] Paper-trading drift monitor + alerting** (roadmap M6 remainder) — paper equity vs the backtest's
  expectation over the same window; alert past a threshold. Journal + reconciliation (the inputs) shipped
  2026-07.
- **[P1] Broker-side trailing stops in paper trading** — submit Alpaca native `trailing_stop` orders alongside
  entries so protection is intraday at the broker; the backtest's same-day-close stop fill is the conservative
  model of exactly that order.
- **[P2] Breakout-based stop re-entry** — the N-day cooldown shipped 2026-07 (`--stop-reentry N`); the
  zero-knob alternative remains unexplored: re-enter only when price reclaims the peak the stop trailed
  (trend proves itself, no time constant, no chop-thrash). Worth a small comparative study.

---

## 2. Ideas to explore (not committed)

- **Document / alt-data lake** (explicitly deferred 2026-07; shape settled in the roadmap parking lot) — raw
  10-K/10-Q text, earnings-call transcripts, news, LLM evals, sentiment: derived **point-in-time panels**
  through the same `PanelSource` seam, keyed to publication timestamps; raw docs beside the store.
- **Screener as a standalone tool** — expose `strategy.weights(ctx).iloc[-1]` as a "scan the universe right now"
  CLI/notebook view (same logic as the backtest's last row).
- **Derived-features layer** (`features/`) — returns, beta, value/quality z-scores as point-in-time panels that
  strategies compose; keeps raw panels and ratios cleanly separated.
- **More strategies** — mean-reversion, breakout, sector-neutral L/S, betting-against-beta, comparables /
  peer-relative value (using SIC).
- **`vectorbt`** for heavy parameter sweeps — only when bt sweep speed actually bottlenecks (hundreds+ of
  configs). The data layer is engine-agnostic, so this is a contained swap behind `engine/runner`.
- **AI-agent / screener signals** as strategy inputs — score → target weights, same interface.
- **DSL / YAML strategy config** — no-code strategy authoring.
- **DuckDB view over `data_store/`** — ad-hoc SQL across the per-ticker parquet files; zero-server, pure
  convenience.

---

## 3. Decisions to make / revisit

- **Survivorship universe source (M4.0 — the open gate)** — Wikipedia change-log (free membership, **no**
  delisted prices) vs Sharadar (cheap, delisted-inclusive prices + tickers-over-time) vs Norgate. Decide here,
  write the outcome in.
- **Multi-asset ETP list** — which wrappers (GLD, USO, …) enter the composite universe, with what labels.
- **`data/sp50.csv` universe wiring** — its CIK column now feeds the EDGAR overlay (2026-07), but it still isn't
  a named universe. Add `sp50`? A generic `--universe-file`?
- **Reconstitution vs delisting** — a frozen monthly/quarterly target can hold a name that delists mid-period;
  prices ffill flat (no P&L), so it's harmless but not strictly correct. Accept or tighten (revisit inside M4).
- **Engine** — stay on `bt` vs adopt `vectorbt`; define the trigger (sweep count / wall-clock).
- **`build_context` default join** — currently `outer` (universe-safe). Confirm this is the right default for
  small explicit `--tickers` lists too.

Decided (kept for the record):

- **Costs (2026-07):** machinery shipped (`--cost-bps` + turnover); default stays `0` — a sub-$1M book in
  liquid large/mid caps — and every frictionless run is stamped. Revisit with M6's *measured* slippage.
- **EPS annual vs TTM (2026-07):** both panels exist (`eps`, `eps_ttm`); each strategy chooses explicitly.
- **Adjusted-price restatement (2026-07):** store as-fetched; new data wins on overlap; `forget()` to refresh.
- **Not a product (2026-07):** personal instrument; `gtm.md` deleted; nothing monetization-shaped gets built.

---

## 4. Known limitations & tech debt

- **Survivorship bias** — `SP500` is *today's* members with an all-`True` mask; labeled on every report and in
  every manifest, not yet fixed (M4).
- **Frictionless by default** — `--cost-bps 0` (deliberate, stamped); short borrow never modeled; long/short
  and high-turnover results flatter accordingly.
- **EDGAR scope** — US filers only. TTM's Q4 reconstruction assumes quarter-additive EPS (share-count moves
  within the year make it approximate). Concept coverage: diluted EPS with basic fallback; other tag variants
  unhandled.
- **L/S beta ≠ exactly 0** on small/biased subsets — expected; tighter on the full universe.
- **Sweep cost** — one full `bt` backtest per name (N × backtests); the store kills the *refetch* cost, the
  compute remains.
- **Legacy request cache** (`core/data_loader.py`) — still the path for intraday; carries its old TODO
  (dict → multi-indexed frame). Daily bars bypass it entirely.
- **Golden-file sensitivity** — the pinned equity values (`tests/test_golden.py`) will flag dependency bumps
  that change `bt`'s arithmetic; that's the point, but expect to re-pin deliberately on upgrades.

---

## 5. Done recently (for context)

- **2026-07:** Cross-industry classification — `ctx.classification(by)` + `build_context(classify=True)` merging
  EDGAR SIC (`sic`/`sic_description`/`sic2`) alongside GICS sector/industry; `strategies/grouping.py`
  (rank/select within group); `sector_neutral_momentum`; `--group-by` + `classification.csv` + a static-labels
  bias stamp.
- **2026-07:** Trust rails (manifest + bias stamps in every artifact, golden-file test, CI, pinned
  `auto_adjust`, panel data-quality gate) · canonical **price store** (additive per-ticker parquet, gap-only
  fetching) · **cost machinery** (`--cost-bps`, turnover) · strategy-attached **guardrails** · EDGAR expansion
  (**TTM EPS**, **shares**/market-cap, **SIC**, full **10-K/10-Q company-facts ingest**, CIK overlay from
  committed CSVs, basic-EPS fallback) · paper-trading **journal + fill reconciliation** + ops guide
  (`05-paper-trading.md`) · hygiene (gtm.md deleted, network-free `clean_ticker`, polygon logger, scratch
  script removed).
- Pluggable data layer: `PanelSource` registry + `DataContext`; strategies migrated to `weights(ctx)`.
- Universe-first backtesting: `SP500` from `data/sp500.csv` (labeled biased) + membership mask; outer-join
  basket runner (NaN-safe over staggered histories).
- Universe **sweep** + alpha/beta **distribution** report (selection-bias antidote for single-asset rules).
- SEC EDGAR point-in-time **EPS** (as-first-filed) + the dollar-neutral **`ls_pe`** long/short.
- Strategies: `buy_n_hold`, `momentum`, `xs_momentum`, `dual_momentum`, `ls_pe`.
