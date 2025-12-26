#!/bin/bash

# Test script for all Demestihas AI services
# This script checks if all services are responding correctly

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo "========================================="
echo "Testing Demestihas AI Services"
echo "========================================="
echo ""

# Function to test a service
test_service() {
    local name=$1
    local url=$2
    local port=$3

    printf "Testing %-20s [Port %s] ... " "$name" "$port"

    if curl -s -f -o /dev/null "$url" 2>/dev/null; then
        echo -e "${GREEN}✅ Healthy${NC}"

        # Try to get JSON response if available
        if [[ "$url" == */health* ]] || [[ "$url" == */api/health* ]]; then
            response=$(curl -s "$url" 2>/dev/null)
            if command -v jq &> /dev/null; then
                echo "  Response: $(echo "$response" | jq -c '.' 2>/dev/null || echo "$response")"
            else
                echo "  Response: $response"
            fi
        fi
        return 0
    else
        echo -e "${RED}❌ Failed${NC}"
        return 1
    fi
}

echo "Checking service health endpoints..."
echo "-----------------------------------------"

# Track results
total=0
passed=0

# Test Redis (using redis-cli if available)
((total++))
printf "Testing %-20s [Port %s] ... " "Redis" "6379"
if command -v redis-cli &> /dev/null; then
    if redis-cli -h localhost -p 6379 ping &> /dev/null; then
        echo -e "${GREEN}✅ Healthy${NC}"
        ((passed++))
    else
        echo -e "${RED}❌ Failed${NC}"
    fi
else
    # Fallback to nc (netcat) if redis-cli not available
    if nc -z localhost 6379 2>/dev/null; then
        echo -e "${GREEN}✅ Port Open${NC}"
        ((passed++))
    else
        echo -e "${RED}❌ Port Closed${NC}"
    fi
fi

# Test HTTP services
services=(
    "Lyco v2|http://localhost:8000/api/health|8000"
    "Huata Calendar|http://localhost:8003/health|8003"
    "MCP Memory|http://localhost:7777/health|7777"
    "EA-AI Bridge|http://localhost:8080/health|8080"
    "Status Dashboard|http://localhost:9999/health|9999"
)

for service in "${services[@]}"; do
    IFS='|' read -r name url port <<< "$service"
    ((total++))
    if test_service "$name" "$url" "$port"; then
        ((passed++))
    fi
done

echo ""
echo "========================================="
echo "Test Results"
echo "========================================="

if [ $passed -eq $total ]; then
    echo -e "${GREEN}✅ All services are healthy! ($passed/$total)${NC}"
    echo ""
    echo "Dashboard available at: http://localhost:9999"
    exit 0
else
    echo -e "${YELLOW}⚠️  Some services failed: $passed/$total passed${NC}"
    echo ""
    echo "Run 'docker-compose ps' to check container status"
    echo "Run 'docker-compose logs [service-name]' to view logs"
    exit 1
fi
