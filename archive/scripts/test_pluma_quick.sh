#!/bin/bash

# Quick Pluma Integration Test
# Verify Pluma deployment and Yanay integration

set -e

VPS_IP="178.156.170.161"
VPS_USER="root"

echo "🧪 QUICK PLUMA INTEGRATION TEST"
echo ""

# Test 1: Container Status
echo "=== CONTAINER STATUS ==="
echo -n "Yanay Container: "
if ssh ${VPS_USER}@${VPS_IP} "docker ps | grep demestihas-yanay" > /dev/null 2>&1; then
    echo "✅ Running"
else
    echo "❌ Not Running"
fi

echo -n "Pluma Container: "
if ssh ${VPS_USER}@${VPS_IP} "docker ps | grep demestihas-pluma" > /dev/null 2>&1; then
    echo "✅ Running"
    PLUMA_RUNNING=true
else
    echo "❌ Not Running"
    PLUMA_RUNNING=false
fi

echo -n "Redis Container: "
if ssh ${VPS_USER}@${VPS_IP} "docker ps | grep lyco-redis" > /dev/null 2>&1; then
    echo "✅ Running"
else
    echo "❌ Not Running"
fi

echo ""

# Test 2: Network Connectivity (only if Pluma is running)
if [ "$PLUMA_RUNNING" = true ]; then
    echo "=== NETWORK CONNECTIVITY ==="
    echo -n "Yanay ↔ Pluma: "
    if ssh ${VPS_USER}@${VPS_IP} "docker exec demestihas-yanay ping -c 1 demestihas-pluma" > /dev/null 2>&1; then
        echo "✅ Connected"
    else
        echo "❌ Failed"
    fi
    
    echo -n "Pluma ↔ Redis: "
    if ssh ${VPS_USER}@${VPS_IP} "docker exec demestihas-pluma python -c 'import redis; r=redis.from_url(\"redis://lyco-redis:6379\"); r.ping()'" > /dev/null 2>&1; then
        echo "✅ Connected"
    else
        echo "❌ Failed"
    fi
    
    echo ""
    
    # Test 3: Pluma Health Check
    echo "=== PLUMA HEALTH CHECK ==="
    if ssh ${VPS_USER}@${VPS_IP} "docker exec demestihas-pluma python -c '
import asyncio
import sys
sys.path.append(\"/app\")
from pluma import PlumaAgent
agent = PlumaAgent()
health = asyncio.run(agent.health_check())
print(f\"Status: {health[\"status\"]}\")
for component, status in health[\"components\"].items():
    print(f\"  {component}: {status}\")
'" 2>/dev/null; then
        echo "✅ Health check completed"
    else
        echo "❌ Health check failed"
    fi
    
    echo ""
fi

# Test 4: Yanay Integration Check  
echo "=== YANAY INTEGRATION ==="
echo -n "Pluma routing code: "
if ssh ${VPS_USER}@${VPS_IP} "cd /root/demestihas-ai && grep -q 'PlumaIntegration' yanay.py" > /dev/null 2>&1; then
    echo "✅ Integrated"
else
    echo "❌ Missing"
fi

echo ""

# Summary
echo "=== INTEGRATION STATUS ==="
if [ "$PLUMA_RUNNING" = true ]; then
    echo "🎉 Pluma Agent: DEPLOYED"
    echo ""
    echo "Ready for testing via @LycurgusBot:"
    echo "• \"draft reply to latest email\""
    echo "• \"organize my inbox\""
    echo "• \"email status\""
    echo ""
    echo "Next steps:"
    echo "1. Set up Gmail OAuth (google_credentials/)"
    echo "2. Test email functionality"
    echo "3. Verify Telegram → Yanay → Pluma routing"
else
    echo "⚠️ Pluma Agent: NOT DEPLOYED"
    echo ""
    echo "Run deployment script:"
    echo "./quick_deploy_pluma.sh"
fi

echo ""
echo "Container Resource Usage:"
ssh ${VPS_USER}@${VPS_IP} "docker stats --no-stream --format 'table {{.Name}}\t{{.CPUPerc}}\t{{.MemUsage}}' | grep -E '(yanay|pluma|redis)' | head -4"

echo ""
echo "✅ Test Complete"
