#!/bin/bash

# Lyco 2.0 Local Deployment Script (No Docker/Redis Required)

echo "============================================="
echo "Lyco 2.0 - Cognitive Prosthetic Deployment"
echo "============================================="

# Kill any existing processes
echo "🔄 Stopping any existing Lyco processes..."
pkill -f "server.py" 2>/dev/null
pkill -f "ambient_capture.py" 2>/dev/null
sleep 2

# Activate virtual environment
echo "🐍 Activating Python environment..."
source venv/bin/activate

# Start the web server in background
echo "🌐 Starting web server on port 8000..."
nohup python server.py > server.log 2>&1 &
SERVER_PID=$!

# Wait for server to start
sleep 3

# Start ambient capture in background
echo "📡 Starting ambient capture (5-minute cycle)..."
nohup python ambient/ambient_capture.py > ambient.log 2>&1 &
CAPTURE_PID=$!

# Wait for everything to initialize
sleep 2

# Check if processes are running
if ps -p $SERVER_PID > /dev/null; then
    echo "✅ Web server running (PID: $SERVER_PID)"
else
    echo "❌ Web server failed to start - check server.log"
    exit 1
fi

if ps -p $CAPTURE_PID > /dev/null; then
    echo "✅ Ambient capture running (PID: $CAPTURE_PID)"
else
    echo "❌ Ambient capture failed to start - check ambient.log"
    exit 1
fi

echo ""
echo "============================================="
echo "🎉 Lyco 2.0 is running!"
echo "============================================="
echo ""
echo "📍 Access UI at: http://localhost:8000"
echo "📊 View server logs: tail -f server.log"
echo "📡 View capture logs: tail -f ambient.log"
echo ""
echo "🛑 To stop everything: ./stop_local.sh"
echo ""
echo "The system will now:"
echo "- Check Gmail/Calendar every 5 minutes"
echo "- Auto-create tasks from commitments"
echo "- Surface one task at a time in the UI"
echo ""
