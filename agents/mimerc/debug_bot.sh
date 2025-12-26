#!/bin/bash
# Debug script to check what version of bot is running

echo "================================"
echo "MiMerc Bot Debug Check"
echo "================================"
echo ""

# Check running processes
echo "Checking for running bot processes..."
ps aux | grep -E "(telegram_bot|mimerc)" | grep -v grep || echo "No bot processes found"
echo ""

# Check if Docker Desktop is running
if pgrep -x "Docker" > /dev/null; then
    echo "✓ Docker Desktop is running"
    echo ""
    
    # Try to find docker command
    if [ -f "/usr/local/bin/docker" ]; then
        echo "Checking Docker containers..."
        /usr/local/bin/docker ps -a --filter "name=mimerc" --format "table {{.Names}}\t{{.Status}}\t{{.CreatedAt}}"
    elif [ -f "/Applications/Docker.app/Contents/Resources/bin/docker" ]; then
        echo "Checking Docker containers..."
        /Applications/Docker.app/Contents/Resources/bin/docker ps -a --filter "name=mimerc" --format "table {{.Names}}\t{{.Status}}\t{{.CreatedAt}}"
    else
        echo "Docker command not found in standard locations"
    fi
else
    echo "✗ Docker Desktop is not running"
fi
echo ""

# Check when files were last modified
echo "Checking when bot files were last modified..."
echo "telegram_bot.py: $(stat -f "%Sm" -t "%Y-%m-%d %H:%M:%S" telegram_bot.py 2>/dev/null || echo "File not found")"
echo "agent.py: $(stat -f "%Sm" -t "%Y-%m-%d %H:%M:%S" agent.py 2>/dev/null || echo "File not found")"
echo ""

# Check for the critical fix in telegram_bot.py
echo "Checking if critical fix is present in telegram_bot.py..."
if grep -q "# Don't initialize grocery_list - checkpointer will load persisted state" telegram_bot.py 2>/dev/null; then
    echo "✅ Fix IS present in telegram_bot.py"
else
    echo "❌ Fix is NOT present in telegram_bot.py"
fi
echo ""

# Check for the critical fix in agent.py
echo "Checking if critical fix is present in agent.py..."
if grep -q "# The grocery_list MUST be included in the return for checkpointer to save it" agent.py 2>/dev/null; then
    echo "✅ Fix IS present in agent.py"
else
    echo "❌ Fix is NOT present in agent.py"
fi
echo ""

echo "================================"
echo "Next Steps:"
echo "================================"
echo ""
echo "If the bot is running in Docker:"
echo "1. The container needs to be rebuilt with the fixed code"
echo "2. Run: docker-compose down && docker-compose build && docker-compose up -d"
echo ""
echo "If the bot is running locally:"
echo "1. Stop the current bot process"
echo "2. Start it again with: python3 telegram_bot.py"
echo ""
echo "The issue is that the RUNNING bot doesn't have the fix,"
echo "even though the fix is in the files."
