#!/bin/bash

echo "🔧 Demestihas AI Container Consolidation"
echo "========================================="

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

cd /Users/menedemestihas/Projects/demestihas-ai

echo -e "${YELLOW}Step 1: Stopping all containers...${NC}"
docker stop $(docker ps -aq) 2>/dev/null

echo -e "${YELLOW}Step 2: Removing incorrectly named containers...${NC}"
docker rm huata-health-fixed 2>/dev/null
docker rm ea-ai-container 2>/dev/null
docker rm demestihas-ai 2>/dev/null

echo -e "${YELLOW}Step 3: Cleaning up old containers...${NC}"
docker container prune -f

echo -e "${YELLOW}Step 4: Ensuring network exists...${NC}"
docker network create demestihas-network 2>/dev/null || echo "Network already exists"

echo -e "${YELLOW}Step 5: Building all services...${NC}"
docker-compose build

echo -e "${YELLOW}Step 6: Starting services with auto-restart...${NC}"
docker-compose up -d

echo -e "${GREEN}Waiting for services to initialize...${NC}"
sleep 10

echo -e "${YELLOW}Step 7: Verifying container status...${NC}"
docker ps --format "table {{.Names}}\t{{.Status}}\t{{.Ports}}"

echo -e "${YELLOW}Step 8: Checking restart policies...${NC}"
for container in $(docker ps --format "{{.Names}}"); do
    policy=$(docker inspect $container | grep -A 1 RestartPolicy | grep Name | cut -d '"' -f 4)
    if [ "$policy" = "unless-stopped" ]; then
        echo -e "${GREEN}✅ $container: restart=$policy${NC}"
    else
        echo -e "${RED}❌ $container: restart=$policy (should be unless-stopped)${NC}"
    fi
done

echo -e "${YELLOW}Step 9: Testing health endpoints...${NC}"
echo -n "Redis: "
redis-cli -h localhost ping 2>/dev/null && echo -e "${GREEN}✅ PONG${NC}" || echo -e "${RED}❌ Failed${NC}"

echo -n "MCP Memory: "
curl -s http://localhost:7777/health | grep -q "healthy" && echo -e "${GREEN}✅ Healthy${NC}" || echo -e "${RED}❌ Failed${NC}"

echo -n "Huata Calendar: "
curl -s http://localhost:8003/health | grep -q "healthy" && echo -e "${GREEN}✅ Healthy${NC}" || echo -e "${RED}❌ Failed${NC}"

echo -n "Lyco v2: "
curl -s http://localhost:8000/api/health | grep -q "healthy" && echo -e "${GREEN}✅ Healthy${NC}" || echo -e "${RED}❌ Failed${NC}"

echo -n "EA-AI Bridge: "
curl -s http://localhost:8081/health | grep -q "healthy" && echo -e "${GREEN}✅ Healthy${NC}" || echo -e "${RED}❌ Failed${NC}"

echo -n "Status Dashboard: "
curl -s http://localhost:9999/health | grep -q "healthy" && echo -e "${GREEN}✅ Healthy${NC}" || echo -e "${RED}❌ Failed${NC}"

echo ""
echo -e "${GREEN}✅ Container consolidation complete!${NC}"
echo -e "${GREEN}All containers will now auto-restart after sleep/wake${NC}"
echo ""
echo "Dashboard: http://localhost:9999"
echo "Lyco UI: http://localhost:8000"
echo "Huata UI: http://localhost:8003"
