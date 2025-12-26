#!/bin/bash

echo "🔧 Fixing Docker Network Communication"
echo "======================================="

# 1. Check current container status
echo -e "\n📊 Current Container Status:"
docker ps --format "table {{.Names}}\t{{.Status}}" | grep -E "NAME|demestihas"

# 2. Verify all containers are on same network
echo -e "\n🌐 Checking Network Configuration:"
docker network inspect demestihas-network --format '{{range .Containers}}{{.Name}} {{end}}' 2>/dev/null || echo "Network not found"

# 3. Restart containers in correct order
echo -e "\n🔄 Restarting containers in dependency order..."

# Stop all first
docker-compose down

# Start with proper dependency resolution
docker-compose up -d redis
sleep 5

docker-compose up -d mcp-memory huata lyco-v2
sleep 10

docker-compose up -d ea-ai-bridge
sleep 5

docker-compose up -d status-dashboard
sleep 5

# 4. Test inter-container connectivity
echo -e "\n🧪 Testing Inter-Container Connectivity:"

# Test from status-dashboard to huata
echo "Testing dashboard → huata connection:"
docker exec demestihas-status-dashboard sh -c "wget -qO- http://huata:8003/health | head -c 100" 2>/dev/null || echo "Failed to connect"

# Test from ea-ai-bridge to huata
echo -e "\nTesting ea-ai-bridge → huata connection:"
docker exec demestihas-ea-ai-bridge sh -c "wget -qO- http://huata:8003/health | head -c 100" 2>/dev/null || echo "Failed to connect"

# 5. Check all health endpoints
echo -e "\n✅ Checking All Health Endpoints:"
echo "Redis: $(curl -s http://localhost:6379 2>&1 | head -c 50)"
echo "MCP Memory: $(curl -s http://localhost:7777/health | jq -r .status 2>/dev/null || echo 'not responding')"
echo "Huata: $(curl -s http://localhost:8003/health | jq -r .status 2>/dev/null || echo 'not responding')"
echo "Lyco: $(curl -s http://localhost:8000/api/health | jq -r .status 2>/dev/null || echo 'not responding')"
echo "EA-AI: $(curl -s http://localhost:8081/health | jq -r .status 2>/dev/null || echo 'not responding')"
echo "Dashboard: $(curl -s http://localhost:9999/health | jq -r .status 2>/dev/null || echo 'not responding')"

# 6. Final status
echo -e "\n📈 Final Status:"
docker-compose ps

echo -e "\n✨ Fix Complete! Check dashboard at http://localhost:9999"
