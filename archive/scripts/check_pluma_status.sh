#!/bin/bash

# Quick Pluma Agent Status Check
# Verify deployment and integration status

set -e

VPS_IP="178.156.170.161"
VPS_USER="root"

# Colors
GREEN='\033[0;32m'
YELLOW='\033[0;33m'
RED='\033[0;31m'
BLUE='\033[0;34m'
NC='\033[0m'

echo -e "${BLUE}🔍 Pluma Agent Status Check${NC}"
echo "Checking multi-agent system health..."
echo ""

# Function to check status
check_status() {
    local service="$1"
    local command="$2"
    
    if ssh ${VPS_USER}@${VPS_IP} "$command" > /dev/null 2>&1; then
        echo -e "✅ ${GREEN}$service${NC} - Operational"
        return 0
    else
        echo -e "❌ ${RED}$service${NC} - Issue detected"
        return 1
    fi
}

# Container status checks
echo -e "${YELLOW}=== Container Health ===${NC}"
check_status "Yanay.ai Orchestrator" "docker ps | grep demestihas-yanay"
check_status "Pluma Email Agent" "docker ps | grep demestihas-pluma" 
check_status "Redis Cache" "docker ps | grep lyco-redis"
check_status "Hermes Audio" "docker ps | grep hermes"

echo ""
echo -e "${YELLOW}=== Service Integration ===${NC}"

# Network connectivity
check_status "Yanay-Pluma Network" "docker exec demestihas-yanay ping -c 1 demestihas-pluma"

# API connectivity  
check_status "Pluma Health Check" "docker exec demestihas-pluma python -c 'import asyncio; import sys; sys.path.append(\"/app\"); from pluma import PlumaAgent; agent = PlumaAgent(); health = asyncio.run(agent.health_check()); exit(0 if health[\"status\"] in [\"healthy\", \"degraded\"] else 1)'"

echo ""
echo -e "${YELLOW}=== Quick System Info ===${NC}"

# Get container resource usage
echo "📊 Container Resources:"
ssh ${VPS_USER}@${VPS_IP} "docker stats --no-stream --format 'table {{.Name}}\t{{.CPUPerc}}\t{{.MemUsage}}' | grep -E '(yanay|pluma|redis|hermes)' | head -5"

echo ""
echo "📧 Pluma Agent Configuration:"
ssh ${VPS_USER}@${VPS_IP} "docker exec demestihas-pluma python -c '
import os
import sys
sys.path.append(\"/app\")
try:
    from pluma import PlumaAgent
    agent = PlumaAgent()
    if hasattr(agent, \"gmail_service\") and agent.gmail_service:
        print(\"Gmail API: ✅ Configured\")
    else:
        print(\"Gmail API: ⚠️  Not configured (run gmail_setup_guide.md)\")
    
    if hasattr(agent, \"claude\") and agent.claude:
        print(\"Claude API: ✅ Connected\")
    else:
        print(\"Claude API: ❌ Not connected\")
        
    if hasattr(agent, \"redis_client\") and agent.redis_client:
        try:
            agent.redis_client.ping()
            print(\"Redis Cache: ✅ Connected\")
        except:
            print(\"Redis Cache: ❌ Connection failed\")
    
except Exception as e:
    print(f\"Agent Check: ❌ {str(e)[:50]}...\")
'"

echo ""
echo -e "${YELLOW}=== Next Steps ===${NC}"

# Check if Gmail is configured
GMAIL_STATUS=$(ssh ${VPS_USER}@${VPS_IP} "ls -la /root/demestihas-ai/google_credentials/ 2>/dev/null | wc -l" || echo "0")

if [ "$GMAIL_STATUS" -gt 2 ]; then
    echo "✅ Gmail credentials detected - Ready for email functionality"
    echo ""
    echo "🧪 Test Commands (via @LycurgusBot):"
    echo "• \"draft reply to latest email\""
    echo "• \"organize my inbox\""
    echo "• \"email status\""
else
    echo "📋 Gmail OAuth Setup Required:"
    echo "1. Follow gmail_setup_guide.md"
    echo "2. Set up Google Cloud Console OAuth"  
    echo "3. Upload credentials to VPS"
    echo "4. Run OAuth authorization flow"
    echo ""
    echo "📖 Setup Guide: ~/Projects/demestihas-ai/gmail_setup_guide.md"
fi

echo ""
echo "📱 Family Integration:"
echo "• Message @LycurgusBot for email assistance"
echo "• Yanay.ai routes email/meeting requests to Pluma"
echo "• 4 agents now available: Nina, Huata, Lyco, Pluma"

echo ""
echo -e "${BLUE}💰 Cost Savings Achieved:${NC}"
echo "• Previous: Fyxer AI \$28/month"
echo "• Current: ~\$5/month (API costs)"
echo "• Savings: \$276/year (83% reduction)"

echo ""
echo -e "${GREEN}🎉 Multi-Agent System Status: Operational${NC}"
