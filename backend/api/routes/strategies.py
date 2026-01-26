from fastapi import APIRouter, HTTPException
from typing import List

from backend.api.models import StrategyInfo
from backend.services.strategy_service import StrategyService

router = APIRouter()
strategy_service = StrategyService()


@router.get("/list", response_model=List[StrategyInfo])
async def list_strategies():
    strategies = strategy_service.list_strategies()
    return strategies


@router.get("/{strategy_name}", response_model=StrategyInfo)
async def get_strategy(strategy_name: str):
    strategy = strategy_service.get_strategy(strategy_name)
    
    if not strategy:
        raise HTTPException(status_code=404, detail="Strategy not found")
    
    return strategy
