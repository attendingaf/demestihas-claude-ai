#!/bin/bash

# Multi-Agent System Health Check
# Verify Yanay + Pluma + Integration Status

set -e

VPS_IP="178.156.170.161"
VPS_USER="root"

echo "🏥 MULTI-AGENT SYSTEM HEALTH CHECK"
echo "Verifying Yanay + Pluma + Integration..."
echo ""

# Function to check and fix container health
check_container() {
    local name="$1"
    local service="$2"
    
    echo -n "🔍 $name Container: "
    
    if ssh ${VPS_USER}@${VPS_IP} "docker ps | grep $service" > /dev/null 2>&1; then
        echo "✅ Running"
        
        # Check if healthy
        health=$(ssh ${VPS_USER}@${VPS_IP} "docker inspect $service | grep '\"Status\":' | head -1" || echo "")
        if [[ "$health" == *"unhealthy"* ]]; then
            echo "  ⚠️  Container marked unhealthy - may need restart"
            return 1
        fi
        return 0
    else
        echo "❌ Not Running"
        return 1
    fi
}

# Check container status
echo "=== CONTAINER HEALTH ==="
check_container "Yanay Orchestrator" "demestihas-yanay"
YANAY_OK=$?

check_container "Pluma Email Agent" "demestihas-pluma"  
PLUMA_OK=$?

check_container "Redis Cache" "lyco-redis"
REDIS_OK=$?

echo ""

# Network connectivity tests
echo "=== NETWORK CONNECTIVITY ==="
if [ $YANAY_OK -eq 0 ] && [ $PLUMA_OK -eq 0 ]; then
    echo -n "🌐 Yanay ↔ Pluma: "
    if ssh ${VPS_USER}@${VPS_IP} "docker exec demestihas-yanay ping -c 1 demestihas-pluma" > /dev/null 2>&1; then
        echo "✅ Connected"
        NETWORK_OK=true
    else
        echo "❌ Failed"
        NETWORK_OK=false
    fi
else
    echo "⏭️  Skipping network test (containers not ready)"
    NETWORK_OK=false
fi

if [ $PLUMA_OK -eq 0 ] && [ $REDIS_OK -eq 0 ]; then
    echo -n "🌐 Pluma ↔ Redis: "
    if ssh ${VPS_USER}@${VPS_IP} "docker exec demestihas-pluma python -c 'import redis; r=redis.from_url(\"redis://lyco-redis:6379\"); r.ping()'" > /dev/null 2>&1; then
        echo "✅ Connected" 
    else
        echo "❌ Failed"
    fi
fi

echo ""

# Integration status
echo "=== INTEGRATION STATUS ==="
echo -n "📧 Yanay-Pluma Routing: "
if ssh ${VPS_USER}@${VPS_IP} "cd /root/demestihas-ai && grep -q 'PlumaIntegration' yanay.py" > /dev/null 2>&1; then
    echo "✅ Integrated"
    INTEGRATION_OK=true
else
    echo "❌ Missing"
    INTEGRATION_OK=false
fi

echo ""

# Overall system status
echo "=== SYSTEM STATUS ==="
if [ $YANAY_OK -eq 0 ] && [ $PLUMA_OK -eq 0 ] && [ "$NETWORK_OK" = true ] && [ "$INTEGRATION_OK" = true ]; then
    echo "🎉 MULTI-AGENT SYSTEM: ✅ OPERATIONAL"
    echo ""
    echo "📧 Email functionality available via @LycurgusBot:"
    echo "• \"draft reply to latest email\""
    echo "• \"organize my inbox\""
    echo "• \"email status\""
    echo ""
    echo "🔧 Next: Set up Gmail OAuth for full functionality"
    echo "   Guide: gmail_setup_guide.md"
    
elif [ $YANAY_OK -eq 0 ] && [ $PLUMA_OK -eq 0 ]; then
    echo "🔄 MULTI-AGENT SYSTEM: ⚠️ PARTIALLY READY"
    echo ""
    echo "Containers running but integration needs work:"
    if [ "$NETWORK_OK" = false ]; then
        echo "• Network connectivity issues"
    fi
    if [ "$INTEGRATION_OK" = false ]; then
        echo "• Missing Yanay-Pluma routing integration"
    fi
    echo ""
    echo "🔧 Restart containers to fix connectivity:"
    echo "   docker-compose restart yanay pluma"
    
else
    echo "🚨 MULTI-AGENT SYSTEM: ❌ ISSUES DETECTED"
    echo ""
    echo "Problems found:"
    if [ $YANAY_OK -ne 0 ]; then
        echo "• Yanay orchestration container not running"
    fi
    if [ $PLUMA_OK -ne 0 ]; then
        echo "• Pluma email agent not running"  
    fi
    if [ $REDIS_OK -ne 0 ]; then
        echo "• Redis cache not running"
    fi
    echo ""
    echo "🔧 Recovery steps:"
    echo "   cd /root/demestihas-ai"
    echo "   docker-compose up -d yanay pluma redis"
fi

echo ""
echo "📊 Container Resource Usage:"
ssh ${VPS_USER}@${VPS_IP} "docker stats --no-stream --format 'table {{.Name}}\t{{.CPUPerc}}\t{{.MemUsage}}' | grep -E '(yanay|pluma|redis)' | head -4"

echo ""
echo "🔍 Recent Container Logs:"
echo "--- Yanay Logs ---"
ssh ${VPS_USER}@${VPS_IP} "docker logs --tail=3 demestihas-yanay 2>/dev/null || echo 'No Yanay logs'"

echo "--- Pluma Logs ---"  
ssh ${VPS_USER}@${VPS_IP} "docker logs --tail=3 demestihas-pluma 2>/dev/null || echo 'No Pluma logs'"

echo ""
echo "✅ Health check complete"
