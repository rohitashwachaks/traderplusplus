#!/bin/bash

echo "🚀 Starting Trader++ FastAPI Backend..."

uvicorn backend.api.main:app --reload --host 0.0.0.0 --port 8000
