# Trader++ Dashboard & API

This document explains how to use the new Streamlit + FastAPI architecture for visualizing and managing your trading platform.

## Architecture Overview

```
┌─────────────────────────────────────────────────────────┐
│                   Streamlit Dashboard                    │
│                    (Port 8501)                          │
│  ┌──────────┬──────────┬──────────┬──────────────┐    │
│  │  Home    │ Backtest │ Results  │  Portfolio   │    │
│  │          │  Runner  │  Viewer  │   Monitor    │    │
│  └──────────┴──────────┴──────────┴──────────────┘    │
└─────────────────────────────────────────────────────────┘
                          │
                    HTTP/WebSocket
                          │
┌─────────────────────────────────────────────────────────┐
│                    FastAPI Backend                       │
│                     (Port 8000)                         │
│  ┌──────────────────────────────────────────────────┐  │
│  │  /api/backtest    - Run & manage backtests      │  │
│  │  /api/portfolio   - Portfolio snapshots         │  │
│  │  /api/strategies  - Strategy library            │  │
│  │  /api/health      - Health check                │  │
│  └──────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────┘
                          │
                          │
┌─────────────────────────────────────────────────────────┐
│              Core Trading Engine                         │
│  ┌──────────────────────────────────────────────────┐  │
│  │  Backtester, Portfolio, Strategies, Executors    │  │
│  └──────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────┘
```

## Quick Start

### 1. Install Dependencies

```bash
pip install -r requirements.txt
```

### 2. Start Both Services

**Option A: Start Everything at Once**
```bash
chmod +x start_all.sh
./start_all.sh
```

**Option B: Start Services Separately**

Terminal 1 - API Backend:
```bash
chmod +x start_api.sh
./start_api.sh
```

Terminal 2 - Streamlit Dashboard:
```bash
chmod +x start_dashboard.sh
./start_dashboard.sh
```

### 3. Access the Dashboard

- **Dashboard**: http://localhost:8501
- **API Documentation**: http://localhost:8000/docs
- **API Health**: http://localhost:8000/api/health

## Features

### 🚀 Backtest Runner
- Configure and run backtests through a web interface
- Real-time progress tracking
- Asynchronous job processing

### 📊 Results Viewer
- Interactive equity curves with Plotly
- Detailed trade logs
- Performance metrics (Sharpe, Sortino, Max Drawdown, etc.)
- Benchmark comparison
- Export to CSV

### 📚 Strategy Library
- Browse available strategies
- View strategy parameters
- Auto-discovery of strategies from codebase

### 💼 Portfolio Monitor
- Real-time portfolio tracking (coming soon)
- Live P&L updates via WebSocket (coming soon)

## API Endpoints

### Backtest Endpoints

**POST /api/backtest/run**
```json
{
  "strategy": "momentum",
  "tickers": "AAPL,MSFT",
  "start_date": "2023-01-01",
  "end_date": "2024-01-01",
  "cash": 100000.0,
  "benchmark": "SPY",
  "interval": "1d",
  "source": "yahoo"
}
```

**GET /api/backtest/{job_id}/status**
- Returns current status and progress

**GET /api/backtest/{job_id}/results**
- Returns complete backtest results

**GET /api/backtest/jobs**
- Lists all backtest jobs

### Strategy Endpoints

**GET /api/strategies/list**
- Returns all available strategies

**GET /api/strategies/{strategy_name}**
- Returns details for a specific strategy

### Portfolio Endpoints

**GET /api/portfolio/{portfolio_id}**
- Returns portfolio snapshot

**WebSocket /api/portfolio/ws/{portfolio_id}**
- Live portfolio updates

## Project Structure

```
traderplusplus/
├── backend/
│   ├── api/
│   │   ├── main.py              # FastAPI app
│   │   ├── models.py            # Pydantic models
│   │   └── routes/
│   │       ├── backtest.py      # Backtest endpoints
│   │       ├── portfolio.py     # Portfolio endpoints
│   │       ├── strategies.py    # Strategy endpoints
│   │       └── health.py        # Health check
│   └── services/
│       ├── backtest_service.py  # Backtest logic
│       ├── portfolio_service.py # Portfolio management
│       └── strategy_service.py  # Strategy discovery
├── dashboard/
│   ├── app.py                   # Main Streamlit app
│   ├── pages/
│   │   ├── home.py
│   │   ├── backtest_runner.py
│   │   ├── results_viewer.py
│   │   ├── portfolio_monitor.py
│   │   └── strategy_library.py
│   └── .streamlit/
│       ├── config.toml
│       └── secrets.toml
├── start_all.sh                 # Start both services
├── start_api.sh                 # Start API only
└── start_dashboard.sh           # Start dashboard only
```

## Migration Path to React

The FastAPI backend is designed to be frontend-agnostic. When you're ready to migrate to React:

1. **Keep the backend as-is** - All endpoints are RESTful and well-documented
2. **Build React frontend** - Use the same API endpoints
3. **Gradual migration** - Run both Streamlit and React in parallel
4. **No backend changes needed** - Just swap the frontend

### Example React Integration

```typescript
// Example API client in React
const runBacktest = async (config: BacktestConfig) => {
  const response = await fetch('http://localhost:8000/api/backtest/run', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(config)
  });
  return response.json();
};
```

## Configuration

### API Base URL

Edit `dashboard/.streamlit/secrets.toml`:
```toml
API_BASE_URL = "http://localhost:8000/api"
```

For production, change to your deployed API URL.

### CORS Settings

Edit `backend/api/main.py` to restrict CORS origins:
```python
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:8501", "https://yourdomain.com"],
    ...
)
```

## Development Tips

### Adding New Endpoints

1. Define Pydantic models in `backend/api/models.py`
2. Create route in `backend/api/routes/`
3. Register route in `backend/api/main.py`
4. Update Streamlit pages to use new endpoint

### Adding New Dashboard Pages

1. Create new file in `dashboard/pages/`
2. Add to navigation in `dashboard/app.py`

### Testing API

Use the auto-generated docs at http://localhost:8000/docs to test endpoints interactively.

## Troubleshooting

**API not connecting:**
- Ensure FastAPI is running on port 8000
- Check `dashboard/.streamlit/secrets.toml` for correct API URL

**Backtest jobs failing:**
- Check API logs for errors
- Verify data source credentials (for Polygon/Alpaca)
- Ensure strategy name is correct

**Streamlit errors:**
- Clear cache: Settings → Clear Cache
- Restart Streamlit server

## Next Steps

1. ✅ Run your first backtest through the dashboard
2. ✅ Explore the strategy library
3. ✅ View detailed results and metrics
4. 🚧 Add live trading integration
5. 🚧 Implement WebSocket real-time updates
6. 🚧 Build React frontend (optional)

---

**Questions?** Check the main README.md or open an issue!
