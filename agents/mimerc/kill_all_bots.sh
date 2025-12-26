#!/bin/bash
# Find and kill all MiMerc bot instances

echo "================================"
echo "🔍 Finding all bot instances"
echo "================================"
echo ""

# Kill all Python telegram bot processes
echo "Stopping all telegram bot processes..."
pkill -f telegram_bot.py
pkill -f mimerc

# Check Docker containers
echo ""
echo "Checking Docker containers..."
if command -v docker &> /dev/null; then
    # Stop any running mimerc containers
    docker stop mimerc-telegram mimerc-agent 2>/dev/null || echo "No Docker containers to stop"
    docker-compose down 2>/dev/null || echo "Docker compose not running"
fi

# Double-check for any remaining Python processes
echo ""
echo "Checking for remaining processes..."
ps aux | grep -E "(telegram_bot|mimerc)" | grep -v grep || echo "✓ No bot processes found"

echo ""
echo "================================"
echo "✅ All instances stopped!"
echo "================================"
echo ""
echo "Now start a SINGLE instance:"
echo ""
echo "Option 1: Run locally"
echo "  export PG_CONNINFO='postgresql://mimerc:mimerc_secure_password@localhost:5433/mimerc_db'"
echo "  python3 telegram_bot.py"
echo ""
echo "Option 2: Run in Docker"
echo "  docker-compose up -d mimerc-telegram"
echo ""
echo "BUT NOT BOTH!"
