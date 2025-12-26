#!/bin/bash
# Verify Yanay Conversation Enhancement

echo "🔍 Yanay.ai Conversation Enhancement Verification"
echo "================================================"
echo ""

# Check conversation content
echo "📝 Checking conversation state for user 7496082572..."
ssh root@178.156.170.161 << 'ENDSSH'
cd /root/demestihas-ai

echo "1️⃣ Conversation turns stored:"
redis-cli LLEN "conv:7496082572:turns"

echo ""
echo "2️⃣ Latest conversation turn:"
redis-cli LINDEX "conv:7496082572:turns" 0 | python3 -m json.tool 2>/dev/null || echo "No JSON data yet"

echo ""
echo "3️⃣ Token usage today:"
TODAY=$(date +%Y-%m-%d)
redis-cli GET "tokens:${TODAY}:7496082572" || echo "0"

echo ""
echo "4️⃣ All conversation keys:"
redis-cli KEYS "conv:*"

echo ""
echo "5️⃣ Yanay container status:"
docker ps | grep yanay | awk '{print $1, $7, $8, $9}'

echo ""
echo "6️⃣ Recent Yanay logs (checking