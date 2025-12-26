#!/bin/bash

echo "🔍 Diagnosing MCP Memory Container..."
echo "========================================="

# Check container status
echo -e "\n📊 Container Status:"
docker ps -a --format "table {{.Names}}\t{{.Status}}\t{{.State}}" | grep mcp-memory

# Check logs for errors
echo -e "\n📝 Last 20 log lines:"
docker logs demestihas-mcp-memory --tail 20 2>&1

# Check if port 7777 is in use
echo -e "\n🔌 Checking port 7777:"
lsof -i :7777 2>/dev/null || echo "Port 7777 is free"

# Attempt to restart
echo -e "\n🔄 Attempting to restart MCP Memory..."
docker restart demestihas-mcp-memory 2>&1

# Wait a moment
sleep 3

# Check if it's running now
echo -e "\n✅ Final Status:"
docker ps --format "table {{.Names}}\t{{.Status}}\t{{.Ports}}" | grep mcp-memory

# Test health endpoint
echo -e "\n🏥 Health Check:"
curl -s http://localhost:7777/health 2>&1 || echo "Health endpoint not responding yet"

echo -e "\n========================================="
echo "✨ Diagnosis complete!"
