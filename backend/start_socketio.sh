#!/bin/bash
# Start backend with Socket.IO support

echo "Installing Socket.IO dependencies..."
pip install python-socketio==5.10.0 python-engineio==4.8.0 httpx

echo "Starting FastAPI backend with WebSocket support..."
echo "API: http://localhost:8000"
echo "WebSocket: ws://localhost:8000/socket.io/"
echo ""

python app.py
