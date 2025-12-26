#!/bin/bash

# Lyco 2.0 Stop Script

echo "🛑 Stopping Lyco 2.0..."

# Kill processes
pkill -f "server.py" 2>/dev/null
pkill -f "ambient_capture.py" 2>/dev/null

echo "✅ All Lyco processes stopped"
echo ""
echo "To restart: ./deploy_local.sh"
