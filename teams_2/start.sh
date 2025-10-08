#!/bin/bash

# Start script for Teams Bot with LangGraph Server integration

echo "Starting Teams Bot with LangGraph integration..."

# Check if .env file exists
if [ ! -f .env ]; then
    echo "⚠️  No .env file found. Creating from template..."
    cp .env.template .env
    echo "Please edit .env file with your configuration before running again."
    exit 1
fi

# Load environment variables
set -a
source .env
set +a

# Check if virtual environment exists
if [ ! -d "../venv" ]; then
    echo "⚠️  Virtual environment not found at ../venv"
    echo "Please create a virtual environment and install requirements:"
    echo "  python3 -m venv ../venv"
    echo "  source ../venv/bin/activate"
    echo "  pip install -r requirements.txt"
    exit 1
fi

# Activate virtual environment
echo "Activating virtual environment..."
source ../venv/bin/activate

# Check if requirements are installed
echo "Checking dependencies..."
python -c "import botbuilder.core" 2>/dev/null
if [ $? -ne 0 ]; then
    echo "Installing requirements..."
    pip install -r requirements.txt
fi

# Check if LangGraph Server is running
echo "Checking LangGraph Server connection..."
curl -s "${LANGGRAPH_SERVER_URL}/ok" > /dev/null
if [ $? -ne 0 ]; then
    echo "⚠️  Warning: Cannot connect to LangGraph Server at ${LANGGRAPH_SERVER_URL}"
    echo "Please ensure LangGraph Server is running:"
    echo "  cd ../main && langgraph dev"
    echo ""
    read -p "Continue anyway? (y/n) " -n 1 -r
    echo
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        exit 1
    fi
fi

echo "Starting Teams Bot server..."
echo "Server will listen on ${HOST}:${PORT}"
echo "Press Ctrl+C to stop"
echo ""

python app.py

