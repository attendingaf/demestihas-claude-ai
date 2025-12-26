#!/bin/bash
# Complete Yanay Fix - Resolves syntax error and adds working enhancement

echo "🔧 Yanay Enhancement Complete Fix"
echo "================================="
echo ""

# Upload safe enhancement
scp ~/Projects/demestihas-ai/yanay_safe_enhancement.py root@178.156.170.161:/root/demestihas-ai/

ssh root@178.156.170.161 << 'ENDSSH'
cd /root/demestihas-ai

echo "1️⃣ Stopping conflicting processes..."
docker-compose down yanay
pkill -f "python.*yanay" 2>/dev/null || true
sleep 2

echo "2️⃣ Creating working yanay.py with enhancement..."

# Create a working enhancement by adding simple imports
cp yanay.py yanay.py.backup.$(date +%Y%m%d_%H%M%S)

# Add the safe import at the end of yanay.py
echo "" >> yanay.py
echo "# Conversation Enhancement" >> yanay.py
echo "try:" >> yanay.py
echo "    from yanay_safe_enhancement import apply_conversation_enhancement, enhance_message_processing" >> yanay.py
echo "    enhancement_loaded = apply_conversation_enhancement()" >> yanay.py
echo "except Exception as e:" >> yanay.py
echo "    print(f'Enhancement not loaded: {e}')" >> yanay.py
echo "    enhancement_loaded = False" >> yanay.py

echo "3️⃣ Testing syntax..."
python3 -m py_compile yanay.py && echo "✅ Syntax valid!" || echo "❌ Syntax error"

echo "4️⃣ Testing managers directly..."
python3 << 'PYTHON'
import sys
sys.path.append('/root/demestihas-ai')

# Test conversation manager
try:
    from conversation_manager import ConversationStateManager
    cm = ConversationStateManager()
    # Add a test turn
    cm.add_turn("test_user", "Hello", "Hi there!")
    turns = cm.get_conversation_context("test_user")
    print(f"✅ ConversationManager works - {len(turns)} turns stored")
except Exception as e:
    print(f"❌ ConversationManager error: {e}")

# Test token manager  
try:
    from token_manager import TokenBudgetManager
    tm = TokenBudgetManager(redis_host='localhost')  # Use localhost outside container
    stats = tm.get_usage_stats()
    print(f"✅ TokenManager works - Daily limit: ${stats['limit_usd']}")
except Exception as e:
    print(f"❌ TokenManager error: {e}")
PYTHON

echo "5️⃣ Starting Yanay with enhancement..."
docker-compose up -d yanay

sleep 5

echo "6️⃣ Checking container health..."
docker ps | grep yanay

echo "7️⃣ Recent logs:"
docker logs --tail 30 demestihas-yanay | grep -E "(enhancement|conversation|Conversation|Enhancement|✅)" || echo "No enhancement logs yet"

echo ""
echo "8️⃣ Verifying conversation tracking:"
redis-cli KEYS "conv:*"

echo ""
echo "✅ Complete! Test with @LycurgusBot:"
echo "  'Hello, how are you?' - Should track conversation"
echo "  'I'm stressed' - Should show in conversation history"
echo ""
echo "Check tracking with: redis-cli LLEN 'conv:YOUR_USER_ID:turns'"

ENDSSH
