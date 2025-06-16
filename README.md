<p align="center">
  <img src="./assets/trader_pp_logo.png" alt="Trader++ Logo" width="100%" style="object-fit:cover;height:300px;object-position:center;border-radius:12px;box-shadow:0 4px 24px rgba(0,0,0,0.10);" />
</p>

> 💡 Why Trader++?
>
> I built Trader++ because I wanted a tool that didn’t lie to me.
>
> I needed something that could:
> - Let me write strategies quickly
> - Simulate realistically
> - Go from backtest → paper → live with zero rewrites
> - Show me how my portfolio’s actually doing, holistically!
>
> Existing tools? Clunky. Proprietary. Not programmable enough.
>
> So I built it — for myself first. Now, it’s for every quant who thinks like a developer.
>
> **Unleash the power of modular, realistic, and extensible portfolio simulation.**

---

## ✨ Why Trader++? 

Trader++ isn’t just another backtesting tool. It’s a full-fledged quant trading engine built for:
- **True Portfolio Simulation:** Manage multiple assets, cash, and trades as real portfolios—not just isolated strategies.
- **Plug-and-Play Modularity:** Swap in new strategies, data sources, or risk guardrails with minimal code.
- **Event-Driven Realism:** Simulate trades, slippage, and portfolio changes in a way that mimics real markets.
- **Powerful Guardrails:** Risk management hooks that go beyond stop-losses—unregister assets, enforce capital limits, and more.
- **Transparent & Hackable:** Built for experimentation, learning, and research. Every core component is swappable and inspectable.

**How is it different from Backtrader, Zipline, or QuantConnect?**
- 🧩 **Cleaner separation of concerns:** Market data, strategies, execution, and portfolio logic are fully decoupled.
- 🛡️ **Advanced guardrails:** Custom risk modules, not just basic stop-losses.
- 💡 **Portfolio as a first-class citizen:** Track capital, trades, and metadata in one place.
- 🧪 **Designed for research:** Easy to debug, extend, and run controlled experiments.
- 🌱 **Open, modern, and Pythonic:** No black boxes, no vendor lock-in, and ready for your next big idea.

---

## 🏆 MVP Roadmap

### 1. Unified Execution Engine
- Common interface: `BacktestExecutor`, `PaperExecutor`, `LiveExecutor`
- Live broker integration (Alpaca, IBKR, TD Ameritrade)
- Real-time slippage, partial fills, latency simulation

### 2. Advanced Strategy Framework
- YAML/DSL config loader for no-code strategies
- Multi-frequency, multi-asset support
- ML model integration (Torch/Sklearn) + MLFlow/W&B logging

### 3. Modular Risk & Portfolio Control
- Position sizing (Kelly, risk parity, volatility targeting)
- Real-time rule engine (e.g., freeze strategy on drawdown)
- Hierarchical/nested portfolios with capital/risk constraints

### 4. Performance & Attribution Analytics
- Alpha, beta, Sharpe, Sortino, Calmar
- Attribution by asset, sector, strategy
- Trade replay and audit trail

### 5. Interactive Visualization
- Streamlit/Dash hybrid dashboard
- Trade timeline, rolling metrics, slippage/turnover/holding histograms

### 6. Scalable Simulation Engine
- Multiprocessed/multithreaded backtesting core
- GPU acceleration for ML strategies
- Clean, event-driven simulation loop

### 7. Data Layer
- SQL/Parquet backend support
- Live feed adapters
- Flexible bar aggregators (time, volume, event)

### 8. AI & Data-Driven Research
- Sentiment and alt-data adapters (Reddit, news, Google Trends)
- Cointegration, Kalman filter, auto-correlation modules

### 9. Tests, Docs, Demos
- Unit tests for each module
- Example strategies (momentum, mean-reversion, breakout)
- Jupyter/Streamlit demo notebooks

---

## 🚦 MVP Status (June 2025)

| Feature                           | Status      | Notes                                                                                                          |
|-----------------------------------|-------------|----------------------------------------------------------------------------------------------------------------|
| Unified Execution Engine          | ✅ Complete | Backtest, Paper, Live modes implemented with shared API. Paper & Live mode requires broker API implementation. |
| Modular Strategy Framework        | ✅ Complete | StrategyBase and example strategies present. Plug-and-play.                                                    |
| Portfolio/Risk Management         | ✅ Complete | Portfolio class, guardrails, position sizing hooks implemented.                                                |
| Analytics & Attribution           | ✅ Partial  | Core metrics (Sharpe, alpha, etc.) present. Some advanced analytics in progress.                               |
| Interactive Dashboard             | ⚠️ Partial | Streamlit app exists, some features stubbed or in progress.                                                    |
| Scalable Simulation Engine        | ⚠️ Partial | Event-driven core present; multiprocessing support basic or planned.                                           |
| Data Layer                        | ✅ Complete | Data ingestion, caching, and basic adapters present.                                                           |
| ML/DSL Integration                | 🚧 Planned  | ML model integration and YAML/DSL loader planned.                                                              |

---

## Next Steps (Post-MVP)
- Expand broker integrations for live trading
- Enhance dashboard with more analytics and controls
- Add ML/DSL strategy support
- Improve test coverage and documentation

---

## 🧠 Objective

Empower quants and developers to:
- Cleanly separate market data, strategies, execution logic, and portfolio tracking
- Run realistic, event-driven backtests and simulations
- Plug-and-play both single-asset and multi-asset strategies

Built for robust experimentation and real-world readiness, with proper portfolio management and capital accounting.

---

## 🗺️ System Architecture

```mermaid
flowchart TD
    subgraph Data Layer
      A[MarketData]
    end
    subgraph Strategy Layer
      B[StrategyBase]
    end
    subgraph Execution Layer
      C[PortfolioExecutor]
      D[Guardrails]
    end
    subgraph Portfolio & Analytics
      E[Portfolio]
      F[Performance Analytics]
    end
    A -- Price/Volume Data --> B
    B -- Signals --> C
    C -- Orders/Trades --> E
    C -- Risk Checks --> D
    D -- Approve/Block Trades --> C
    E -- Holdings/PnL --> F
    F -- Reports --> E
```

---

## 🏗️ Project Structure & Architecture

- `contracts/` — Core contracts and abstract base classes (Portfolio, StrategyBase, Executor)
- `core/` — Core logic, execution engines, simulation loop
- `strategies/` — Example and user strategies (momentum, buy & hold, etc.)
- `data_ingestion/`, `data_cache/` — Data loaders, adapters, and caching for reproducible research
- `analytics/`, `ml_engine/` — Analytics, reporting, and ML integrations
- `dashboard/` — Streamlit/Dash dashboard for visualization
- `run_backtest.py` — CLI entry point to run backtests
- `main.py`, `run/` — Additional CLI tools and runners

---

## 🚦 Development Roadmap (Next Steps)

1. **Finalize Core Contracts**
   - Audit and refine `Portfolio`, `StrategyBase`, and `PortfolioExecutor` for strict modularity and safety (no future leaks).
2. **Strategy API**
   - Enforce and document the `generate_signals` interface. Add more example strategies.
3. **Backtesting Engine**
   - Expand test coverage and logging in `run_backtest.py` and `core/executors/backtest.py`.
4. **Data Layer**
   - Ensure robust, reproducible data ingestion and caching. Document data contracts.
5. **CLI & Developer Experience**
   - Improve CLI usability and add clear usage examples.
6. **Dashboard & Analytics**
   - Expand analytics and dashboard integration for portfolio and strategy reporting.
7. **Documentation**
   - Add docstrings, inline docs, and contribution guidelines for new modules and strategies.

---

## 🔧 Core Components

| Module            | Purpose                                                                 |
|-------------------|-------------------------------------------------------------------------|
| Portfolio         | Tracks assets, cash, trades, and strategy metadata. Self-contained unit. |
| PortfolioExecutor | Orchestrates strategy execution, manages trade logic, evaluates guards.  |
| MarketData        | Historical price data & sliding window views for strategies.             |
| StrategyBase      | Interface for strategy design, single/multi-asset support.               |
| Backtester        | Runs simulations, exports performance reports and logs.                  |

---

## 💡 Main Features

- 📈 **Backtesting Engine** — Realistic execution, guardrails, cash shares checks
- 🧠 **Pluggable Strategy Interface** — Stateful/stateless signal generation
- 💼 **Portfolio Tracking** — Accurate PnL with trade logs, equity curves
- 🛡️ **GuardrailBase System** — Risk management hooks (stop-loss, asset unregister)
- 📊 **Performance Reporting** — Sharpe, max drawdown, win rate, CAGR, more
- 🔬 **Benchmark Comparison** — Alpha, beta, vs SPY or other tickers
- 🧪 **Test Strategies** — Debug pipeline (e.g., “buy once on day 1”)

---

## 🚀 Quickstart

1. **Install Requirements**
   ```bash
   pip install -r requirements.txt
   ```
2. **Run a Backtest**
   ```bash
   python main.py --start=2022-05-29 --end=2025-05-29 --cash 50000 --plot --export --tickers=META --refresh --strategy=momentum --benchmark=META --guardrail=trailing_stop_loss
   ```
3. **Add a New Strategy**
   - Implement a new class in `strategies/` inheriting from `StrategyBase` and implementing `generate_signals()`.
   - Register your strategy by importing it in `strategies/__init__.py`.

4  **Add a New Guardrail**
   - Implement a new class in `guardrails/` inheriting from `GuardrailBase` and implementing `evaluate()`.
   - Register your guardrail by importing it in `guardrails/__init__.py`.
---

## 🤝 Contributing

[//]: # (- See the Development Roadmap above for high-priority areas.)
- Add new strategies, data adapters, or analytics modules as composable units.
- Follow modular design and document your code.
- PRs and issues welcome!

---

## 🌱 Vision for Future Work

See the MVP Roadmap above for our ambitious next steps!

---

## 📄 License

Distributed under the MIT License.

---

## 📬 Contact

Open an issue or reach out via GitHub for questions and collaboration!

---

Enjoy building and experimenting with Trader++! 🚀
