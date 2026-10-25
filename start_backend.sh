#!/bin/bash

# SentinelFlux Backend Startup Script
# This script helps initialize and run the backend with proper logging

echo "🚀 Starting SentinelFlux Backend"
echo "================================="

# Check if .env file exists
if [ ! -f ".env" ]; then
    echo "⚠️  No .env file found. Creating from template..."
    if [ -f ".env.example" ]; then
        cp .env.example .env
        echo "✅ Created .env from .env.example"
        echo "📝 Please edit .env with your actual credentials before continuing"
        exit 1
    else
        echo "❌ No .env.example found. Please create .env manually"
        exit 1
    fi
fi

# Source environment variables
source .env

# Create logs directory if it doesn't exist
mkdir -p logs

# Check if running in local mode
if [ "${AT_LOCAL_MACHINE}" = "true" ]; then
    echo "🏠 Running in LOCAL development mode"
    echo "📍 Using localhost connections"
else
    echo "🏭 Running in PRODUCTION mode"
    echo "📍 Using environment-configured connections"
fi

# Check if DEBUG is enabled
if [ "${DEBUG}" = "true" ]; then
    echo "🐛 Debug logging enabled"
else
    echo "📊 Production logging mode"
fi

echo "================================="
echo "Starting FastAPI application..."
echo "================================="

# Start the application
if [ "${DEBUG}" = "true" ]; then
    # Development mode with auto-reload
    uvicorn main:app --reload --host 0.0.0.0 --port 8000 --log-level info
else
    # Production mode
    uvicorn main:app --host 0.0.0.0 --port 8000 --workers 4
fi
