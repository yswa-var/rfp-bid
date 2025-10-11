#!/bin/bash

# Startup script for DOCX Agent Backend

echo "🚀 Starting DOCX Agent Backend..."

# Load environment variables
if [ -f .env ]; then
    export $(cat .env | grep -v '#' | xargs)
    echo "✅ Loaded environment variables from .env"
else
    echo "⚠️  No .env file found. Using defaults..."
fi

# Check if LangGraph server is running (if using remote mode)
if [ ! -z "$LANGGRAPH_URL" ]; then
    echo "🔍 Checking LangGraph server at $LANGGRAPH_URL..."
    if curl -s "$LANGGRAPH_URL/health" > /dev/null 2>&1; then
        echo "✅ LangGraph server is reachable"
    else
        echo "⚠️  Warning: Cannot reach LangGraph server at $LANGGRAPH_URL"
        echo "   Make sure the server is running with: cd ../main && langgraph dev"
        echo "   Or leave LANGGRAPH_URL empty in .env to use local execution"
    fi
fi

# Set default port if not specified
PORT=${PORT:-8080}
HOST=${HOST:-0.0.0.0}

echo "📡 Starting backend server on $HOST:$PORT..."
echo "📖 API Documentation: http://localhost:$PORT/docs"
echo ""

# Start the server
if [ "$DEBUG" = "true" ]; then
    # Development mode with auto-reload
    uvicorn app:app --host $HOST --port $PORT --reload
else
    # Production mode
    gunicorn app:app \
        --workers 4 \
        --worker-class uvicorn.workers.UvicornWorker \
        --bind $HOST:$PORT \
        --timeout 120 \
        --access-logfile - \
        --error-logfile -
fi
