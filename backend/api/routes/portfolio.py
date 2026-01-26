from fastapi import APIRouter, HTTPException, WebSocket, WebSocketDisconnect
from typing import List
import json

from backend.api.models import PortfolioSnapshot
from backend.services.portfolio_service import PortfolioService

router = APIRouter()
portfolio_service = PortfolioService()


@router.get("/{portfolio_id}", response_model=PortfolioSnapshot)
async def get_portfolio(portfolio_id: str):
    portfolio = portfolio_service.get_portfolio(portfolio_id)
    
    if not portfolio:
        raise HTTPException(status_code=404, detail="Portfolio not found")
    
    return portfolio


@router.get("/", response_model=List[PortfolioSnapshot])
async def list_portfolios():
    portfolios = portfolio_service.list_portfolios()
    return portfolios


@router.websocket("/ws/{portfolio_id}")
async def portfolio_websocket(websocket: WebSocket, portfolio_id: str):
    await websocket.accept()
    
    try:
        while True:
            update = await portfolio_service.get_live_update(portfolio_id)
            
            if update:
                await websocket.send_json(update.dict())
            
            data = await websocket.receive_text()
            
            if data == "ping":
                await websocket.send_text("pong")
    
    except WebSocketDisconnect:
        print(f"WebSocket disconnected for portfolio {portfolio_id}")
    except Exception as e:
        print(f"WebSocket error: {e}")
        await websocket.close()
