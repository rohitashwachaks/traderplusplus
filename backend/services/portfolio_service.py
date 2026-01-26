from typing import Dict, Optional, List
from datetime import datetime
import asyncio

from backend.api.models import PortfolioSnapshot, LiveUpdate


class PortfolioService:
    def __init__(self):
        self.portfolios: Dict[str, Dict] = {}
    
    def get_portfolio(self, portfolio_id: str) -> Optional[PortfolioSnapshot]:
        if portfolio_id not in self.portfolios:
            return None
        
        portfolio_data = self.portfolios[portfolio_id]
        
        return PortfolioSnapshot(
            portfolio_id=portfolio_id,
            name=portfolio_data["name"],
            tickers=portfolio_data["tickers"],
            cash=portfolio_data["cash"],
            positions=portfolio_data["positions"],
            net_worth=portfolio_data["net_worth"],
            total_return=portfolio_data["total_return"],
            timestamp=portfolio_data["timestamp"]
        )
    
    def list_portfolios(self) -> List[PortfolioSnapshot]:
        return [
            self.get_portfolio(portfolio_id)
            for portfolio_id in self.portfolios.keys()
        ]
    
    async def get_live_update(self, portfolio_id: str) -> Optional[LiveUpdate]:
        await asyncio.sleep(1)
        
        if portfolio_id not in self.portfolios:
            return None
        
        return LiveUpdate(
            portfolio_id=portfolio_id,
            timestamp=datetime.now(),
            event_type="heartbeat",
            data={"status": "active"}
        )
    
    def register_portfolio(self, portfolio_id: str, portfolio_data: Dict):
        self.portfolios[portfolio_id] = portfolio_data
    
    def update_portfolio(self, portfolio_id: str, updates: Dict):
        if portfolio_id in self.portfolios:
            self.portfolios[portfolio_id].update(updates)
