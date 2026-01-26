from fastapi import APIRouter, HTTPException, BackgroundTasks
from typing import Dict
import uuid
from datetime import datetime
import pandas as pd

from backend.api.models import BacktestConfig, BacktestResponse, BacktestStatus, BacktestResults
from backend.services.backtest_service import BacktestService

router = APIRouter()
backtest_service = BacktestService()


@router.post("/run", response_model=BacktestResponse)
async def run_backtest(config: BacktestConfig, background_tasks: BackgroundTasks):
    job_id = str(uuid.uuid4())
    
    background_tasks.add_task(
        backtest_service.run_backtest,
        job_id=job_id,
        config=config
    )
    
    return BacktestResponse(
        job_id=job_id,
        status="queued",
        message="Backtest job queued successfully"
    )


@router.get("/{job_id}/status", response_model=BacktestStatus)
async def get_backtest_status(job_id: str):
    status = backtest_service.get_status(job_id)
    
    if not status:
        raise HTTPException(status_code=404, detail="Job not found")
    
    return status


@router.get("/{job_id}/results", response_model=BacktestResults)
async def get_backtest_results(job_id: str):
    results = backtest_service.get_results(job_id)
    
    if not results:
        raise HTTPException(status_code=404, detail="Results not found")
    
    if results.get("status") != "completed":
        raise HTTPException(
            status_code=400,
            detail=f"Backtest not completed. Current status: {results.get('status')}"
        )
    
    return results["data"]


@router.get("/jobs", response_model=Dict)
async def list_backtest_jobs():
    jobs = backtest_service.list_jobs()
    return {"jobs": jobs}


@router.delete("/{job_id}")
async def delete_backtest_job(job_id: str):
    success = backtest_service.delete_job(job_id)
    
    if not success:
        raise HTTPException(status_code=404, detail="Job not found")
    
    return {"message": f"Job {job_id} deleted successfully"}
