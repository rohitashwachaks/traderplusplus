from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from backend.api.routes import backtest, portfolio, strategies, health

app = FastAPI(
    title="Trader++ API",
    description="Backend API for Trader++ trading engine",
    version="0.1.0"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(health.router, prefix="/api", tags=["health"])
app.include_router(backtest.router, prefix="/api/backtest", tags=["backtest"])
app.include_router(portfolio.router, prefix="/api/portfolio", tags=["portfolio"])
app.include_router(strategies.router, prefix="/api/strategies", tags=["strategies"])


@app.get("/")
async def root():
    return {
        "message": "Trader++ API",
        "version": "0.1.0",
        "docs": "/docs"
    }
