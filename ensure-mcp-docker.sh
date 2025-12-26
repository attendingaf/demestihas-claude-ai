#!/bin/bash
# Ensure MCP Memory runs in Docker, not locally
# This script prevents the local Node.js process from running
# and ensures the Docker container is started instead

echo "🐳 Ensuring MCP Memory runs in Docker..."

# Check if local process is running
if lsof -i :7777 > /dev/null 2>&1; then
    echo "⚠️  Local process detected on port 7777"

    # Check if it's launchctl managed
    if launchctl list | grep -q "com.demestihas.memory-api"; then
        echo "   Unloading LaunchAgent..."
        launchctl unload ~/Library/LaunchAgents/com.demestihas.memory-api.plist 2>/dev/null
    fi

    # Kill any remaining process
    PID=$(lsof -ti :7777)
    if [ ! -z "$PID" ]; then
        echo "   Stopping local process (PID: $PID)..."
        kill -TERM $PID 2>/dev/null
        sleep 3
    fi
fi

# Verify port is free
if lsof -i :7777 > /dev/null 2>&1; then
    echo "❌ Failed to stop local process on port 7777"
    exit 1
fi

echo "✅ Port 7777 is free"

# Check if Docker container exists
if docker ps -a --format "{{.Names}}" | grep -q "^demestihas-mcp-memory$"; then
    # Check if container is already running
    if docker ps --format "{{.Names}}" | grep -q "^demestihas-mcp-memory$"; then
        echo "✅ Docker container is already running"
    else
        echo "🚀 Starting Docker container..."
        cd /Users/menedemestihas/Projects/demestihas-ai
        docker-compose up -d mcp-memory

        # Wait for container to be healthy
        echo "⏳ Waiting for container to be healthy..."
        for i in {1..30}; do
            if curl -s http://localhost:7777/health > /dev/null 2>&1; then
                echo "✅ Container is healthy"
                break
            fi
            sleep 1
            if [ $i -eq 30 ]; then
                echo "⚠️  Container did not become healthy in 30 seconds"
            fi
        done
    fi
else
    echo "🚀 Creating and starting Docker container..."
    cd /Users/menedemestihas/Projects/demestihas-ai
    docker-compose up -d mcp-memory

    # Wait for container to be healthy
    echo "⏳ Waiting for container to be healthy..."
    for i in {1..30}; do
        if curl -s http://localhost:7777/health > /dev/null 2>&1; then
            echo "✅ Container is healthy"
            break
        fi
        sleep 1
        if [ $i -eq 30 ]; then
            echo "⚠️  Container did not become healthy in 30 seconds"
        fi
    done
fi

# Verify health and show stats
echo ""
echo "📊 MCP Memory Status:"
curl -s http://localhost:7777/health | python3 -c "
import json, sys
data = json.load(sys.stdin)
print(f'   Status: {data[\"status\"]}')
print(f'   Version: {data[\"version\"]}')
print(f'   Total Memories: {data[\"stats\"][\"totalMemories\"]}')
print(f'   Embedding Coverage: {data[\"stats\"][\"embeddingCoverage\"]}')
print(f'   Cloud Status: {data[\"stats\"][\"cloudStatus\"]}')
" 2>/dev/null || echo "   ⚠️  Could not retrieve health stats"

echo ""
echo "✅ MCP Memory is running in Docker container!"
echo "   Container: demestihas-mcp-memory"
echo "   Port: 7777"
echo "   Logs: docker logs demestihas-mcp-memory"
