from typing import Dict, Optional, List
from datetime import datetime
import traceback

from analytics.performance_evaluator import PerformanceEvaluator
from core.backtester import Backtester
from executors.backtest import BacktestExecutor
from core.data_loader import DataIngestionManager
from core.market_data import MarketData
from contracts.portfolio import Portfolio
from backend.api.models import BacktestConfig, BacktestStatus, BacktestResults


class BacktestService:
    def __init__(self):
        self.jobs: Dict[str, Dict] = {}
    
    def run_backtest(self, job_id: str, config: BacktestConfig):
        self.jobs[job_id] = {
            "status": "running",
            "progress": 0.0,
            "started_at": datetime.now(),
            "config": config.dict()
        }
        
        try:
            portfolio = Portfolio(
                name=f"{config.strategy.capitalize()}-Portfolio",
                tickers=config.tickers,
                benchmark=config.benchmark,
                starting_cash=config.cash,
                strategy=config.strategy,
                guardrail=config.guardrail,
                metadata={"source": "API", "job_id": job_id}
            )
            
            tickers = portfolio.tickers
            strategy = portfolio.strategy
            
            ingestion = DataIngestionManager(source=config.source)
            market_data = MarketData(ingestion, simulation_start_date=config.start_date)
            
            executor = BacktestExecutor(portfolio=portfolio, market_data=market_data)
            
            bt = Backtester(
                strategy=strategy,
                market_data=market_data,
                portfolio=portfolio,
                executor=executor
            )
            
            self.jobs[job_id]["progress"] = 0.3
            
            bt.run(
                start_date=config.start_date,
                end_date=config.end_date,
                interval=config.interval,
                period=config.period
            )
            
            self.jobs[job_id]["progress"] = 0.8
            
            equity_curve = bt.get_equity_curve()
            trade_log = bt.get_trade_log()
            
            metrics = {}
            try:
                evaluator = PerformanceEvaluator(
                    equity_curve['net_worth'],
                    equity_curve['benchmark']
                )
                metrics = evaluator.compute_metrics()
            except Exception as e:
                metrics = {"error": str(e)}
            
            results = BacktestResults(
                job_id=job_id,
                portfolio_name=portfolio.name,
                tickers=tickers,
                start_date=config.start_date,
                end_date=config.end_date,
                starting_cash=config.cash,
                final_net_worth=bt.get_final_net_worth(),
                total_return=(bt.get_final_net_worth() - config.cash) / config.cash * 100,
                equity_curve=equity_curve.reset_index().to_dict('records'),
                trade_log=trade_log.to_dict('records'),
                metrics=metrics
            )
            
            self.jobs[job_id] = {
                "status": "completed",
                "progress": 1.0,
                "started_at": self.jobs[job_id]["started_at"],
                "completed_at": datetime.now(),
                "config": config.dict(),
                "data": results
            }
            
        except Exception as e:
            self.jobs[job_id] = {
                "status": "failed",
                "progress": self.jobs[job_id].get("progress", 0.0),
                "started_at": self.jobs[job_id]["started_at"],
                "failed_at": datetime.now(),
                "config": config.dict(),
                "error": str(e),
                "traceback": traceback.format_exc()
            }
    
    def get_status(self, job_id: str) -> Optional[BacktestStatus]:
        if job_id not in self.jobs:
            return None
        
        job = self.jobs[job_id]
        return BacktestStatus(
            job_id=job_id,
            status=job["status"],
            progress=job.get("progress"),
            message=job.get("message"),
            error=job.get("error")
        )
    
    def get_results(self, job_id: str) -> Optional[Dict]:
        if job_id not in self.jobs:
            return None
        
        return self.jobs[job_id]
    
    def list_jobs(self) -> List[Dict]:
        return [
            {
                "job_id": job_id,
                "status": job["status"],
                "started_at": job.get("started_at").isoformat() if job.get("started_at") else None,
                "config": job.get("config", {})
            }
            for job_id, job in self.jobs.items()
        ]
    
    def delete_job(self, job_id: str) -> bool:
        if job_id not in self.jobs:
            return False
        
        del self.jobs[job_id]
        return True
