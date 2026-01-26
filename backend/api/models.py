from datetime import datetime
from typing import Optional, List, Dict, Any
from pydantic import BaseModel, Field


class BacktestConfig(BaseModel):
    strategy: str = Field(..., description="Strategy name (e.g., momentum, buy_n_hold)")
    tickers: str = Field(..., description="Comma-separated list of tickers")
    start_date: str = Field(..., description="Start date (YYYY-MM-DD)")
    end_date: str = Field(..., description="End date (YYYY-MM-DD)")
    cash: float = Field(default=100000.0, description="Starting cash")
    benchmark: Optional[str] = Field(default=None, description="Benchmark ticker")
    guardrail: Optional[str] = Field(default=None, description="Guardrail strategy")
    interval: str = Field(default="1d", description="Data interval")
    period: str = Field(default="5y", description="Data period")
    source: str = Field(default="yahoo", description="Data source")
    refresh: bool = Field(default=False, description="Force data refresh")


class BacktestResponse(BaseModel):
    job_id: str
    status: str
    message: str


class BacktestStatus(BaseModel):
    job_id: str
    status: str
    progress: Optional[float] = None
    message: Optional[str] = None
    error: Optional[str] = None


class BacktestResults(BaseModel):
    job_id: str
    portfolio_name: str
    tickers: List[str]
    start_date: str
    end_date: str
    starting_cash: float
    final_net_worth: float
    total_return: float
    equity_curve: List[Dict[str, Any]]
    trade_log: List[Dict[str, Any]]
    metrics: Dict[str, Any]


class PortfolioSnapshot(BaseModel):
    portfolio_id: str
    name: str
    tickers: List[str]
    cash: float
    positions: Dict[str, Any]
    net_worth: float
    total_return: float
    timestamp: datetime


class StrategyInfo(BaseModel):
    name: str
    description: str
    category: str
    parameters: Dict[str, Any]


class LiveUpdate(BaseModel):
    portfolio_id: str
    timestamp: datetime
    event_type: str
    data: Dict[str, Any]
