#!/bin/bash

echo "🔄 Restarting services for demo..."

# Kill existing processes
echo "🛑 Stopping existing services..."
pkill -f "python.*backend/app.py" || true
pkill -f "uvicorn app:app" || true
pkill -f "python.*teams/app.py" || true

echo "⏳ Waiting for processes to stop..."
sleep 3

# Start backend
echo "🚀 Starting backend..."
cd backend
python app.py &
BACKEND_PID=$!
cd ..

echo "⏳ Waiting for backend to start..."
sleep 5

# Start Teams bot
echo "🤖 Starting Teams bot..."
cd teams
python app.py &
TEAMS_PID=$!
cd ..

echo "✅ Services restarted!"
echo "   Backend PID: $BACKEND_PID"
echo "   Teams Bot PID: $TEAMS_PID"
echo ""
echo "📋 To check status:"
echo "   ps aux | grep python"
echo ""
echo "🎯 Demo is ready!"
