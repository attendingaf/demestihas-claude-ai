#!/bin/bash
# Quick diagnostic and fix script for Yanay enhancement

echo "🔍 Yanay Enhancement Diagnostic"
echo "================================"
echo ""

ssh root@178.156.170.161 << 'ENDSSH'
cd /root/demestihas-ai

echo "1️⃣ Checking if enhancement methods exist in yanay.py:"
echo "---------------------------------------------------"
grep -c "evaluate_response_mode" yanay.py && echo "✅ evaluate_response_mode found" || echo "❌ evaluate_response_mode missing"
grep -c "opus_conversation" yanay.py && echo "✅ opus_conversation found" || echo "❌ opus_conversation missing"
grep -c "conversation_manager" yanay.py && echo "✅ conversation_manager import found" || echo "❌ conversation_manager import missing"
grep -c "token_manager" yanay.py && echo "✅ token_manager import found" || echo "❌ token_manager import missing"

echo ""
echo "2️⃣ Checking conversation data:"
echo "----------------------------"
echo "User ID: 7496082572"
echo "Conversation turns stored: $(redis-cli LLEN "conv:7496082572:turns")"
echo "Latest turn:"
redis-cli LINDEX "conv:7496082572:turns" 0 | python3 -c "import sys, json; data=json.loads(sys.stdin.read()); print(f'  Message: {data.get(\"message\",\"N/A\")[:50]}...'); print(f'  Response: {data.get(\"response\",\"N/A\")[:50]}...'); print(f'  Emotion: {data.get(\"emotion\",\"N/A\")}'); print(f'  Time: {data.get(\"timestamp\",\"N/A\")}')" 2>/dev/null || echo "  No structured data"

echo ""
echo "3️⃣ Checking current Yanay process:"
echo "--------------------------------"
docker logs --tail 30 demestihas-yanay | grep -E "(opus|conversation|token|budget|routing|evaluate)" || echo "No enhancement logs found"

echo ""
echo "4️⃣ Testing if Opus is configured:"
echo "-------------------------------"
grep "ANTHROPIC_OPUS_KEY" .env && echo "✅ Opus key configured" || echo "❌ Opus key not configured"

echo ""
echo "5️⃣ Quick test of managers:"
echo "------------------------"
python3 << 'PYTHON'
import sys
sys.path.append('/root/demestihas-ai')

try:
    from conversation_manager import ConversationStateManager
    print("✅ ConversationStateManager imports successfully")
    mgr = ConversationStateManager()
    print("✅ ConversationStateManager initializes")
except Exception as e:
    print(f"❌ ConversationStateManager error: {e}")

try:
    from token_manager import TokenBudgetManager
    print("✅ TokenBudgetManager imports successfully")
    mgr = TokenBudgetManager()
    stats = mgr.get_usage_stats()
    print(f"✅ TokenBudgetManager works - Daily budget: ${stats['limit_usd']}")
except Exception as e:
    print(f"❌ TokenBudgetManager error: {e}")
PYTHON

echo ""
echo "6️⃣ Container health:"
echo "------------------"
docker ps | grep yanay && echo "✅ Yanay container running" || echo "❌ Yanay container not running"

ENDSSH

echo ""
echo "🔧 Quick Fix Commands:"
echo "====================="
echo ""
echo "If methods are missing, run:"
echo "  ssh root@178.156.170.161"
echo "  cd /root/demestihas-ai"
echo "  python3 yanay_integrator.py"
echo "  docker-compose restart yanay"
echo ""
echo "To trigger token tracking, send:"
echo "  'I'm feeling stressed' (triggers Opus conversation)"
echo ""
echo "To check if working:"
echo "  redis-cli GET 'tokens:$(date +%Y-%m-%d):7496082572'"
