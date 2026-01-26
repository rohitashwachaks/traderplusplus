#!/bin/bash

echo "🚀 Starting Trader++ Full Stack..."
echo ""

trap 'kill 0' EXIT

echo "Starting FastAPI backend on port 8000..."
uvicorn backend.api.main:app --reload --host 0.0.0.0 --port 8000 &

sleep 3

echo ""
echo "Starting Streamlit dashboard on port 8501..."
streamlit run dashboard/app.py &

echo ""
echo "✅ Both services started!"
echo "📊 Dashboard: http://localhost:8501"
echo "🔌 API Docs: http://localhost:8000/docs"
echo ""
echo "Press Ctrl+C to stop all services"

wait
