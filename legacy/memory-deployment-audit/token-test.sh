#!/bin/bash

# Step 1: Generate fresh JWT token for user 'mene'
echo "=== GENERATING FRESH JWT TOKEN ===" | tee token-generation.log

curl -X POST "http://localhost:8000/auth/token?user_id=mene" \
  -H "Content-Type: application/json" \
  2>&1 | tee -a token-generation.log

# Step 2: Extract and save the token
echo "" | tee -a token-generation.log
echo "=== EXTRACTING TOKEN ===" | tee -a token-generation.log

TOKEN=$(curl -s -X POST "http://localhost:8000/auth/token?user_id=mene" | \
  python3 -c "import json,sys; print(json.load(sys.stdin)['access_token'])" 2>/dev/null)

if [ -n "$TOKEN" ]; then
  echo "$TOKEN" > /root/jwt-token-only.txt
  echo "✅ Token saved to /root/jwt-token-only.txt" | tee -a token-generation.log
  
  # Verify token format
  echo "" | tee -a token-generation.log
  echo "Token preview: ${TOKEN:0:50}..." | tee -a token-generation.log
  
  # Decode token to check expiry
  echo "" | tee -a token-generation.log
  echo "=== TOKEN DETAILS ===" | tee -a token-generation.log
  echo "$TOKEN" | cut -d'.' -f2 | base64 -d 2>/dev/null | python3 -m json.tool | tee -a token-generation.log
  
else
  echo "❌ Failed to generate token" | tee -a token-generation.log
  exit 1
fi

# Step 3: Test API access with new token
echo "" | tee -a token-generation.log
echo "=== TESTING API ACCESS ===" | tee -a token-generation.log

# Test memory/stats endpoint
curl -s -X GET "http://localhost:8000/memory/stats" \
  -H "Authorization: Bearer $TOKEN" \
  2>&1 | python3 -m json.tool | tee -a token-generation.log

# Step 4: Test memory storage
echo "" | tee -a token-generation.log
echo "=== TESTING MEMORY STORAGE ===" | tee -a token-generation.log

TIMESTAMP=$(date -u +"%Y-%m-%dT%H:%M:%SZ")
TEST_CONTENT=$(cat <<EOF
{
  "content": "Memory system integration test - $TIMESTAMP",
  "metadata": {
    "contexts": ["system"],
    "importance": 5,
    "tags": ["test", "integration"],
    "created_at": "$TIMESTAMP",
    "source": "deployment_validation"
  }
}
EOF
)

curl -s -X POST "http://localhost:8000/memory/store" \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d "content=$(echo "$TEST_CONTENT" | jq -r tostring)&memory_type=private" \
  2>&1 | python3 -m json.tool | tee -a token-generation.log

# Step 5: Verify memory was stored
echo "" | tee -a token-generation.log
echo "=== VERIFYING STORAGE ===" | tee -a token-generation.log

docker exec demestihas-graphdb redis-cli \
  GRAPH.QUERY mene_memory "MATCH (n:Memory) RETURN count(n)" \
  2>&1 | tee -a token-generation.log

# Step 6: Retrieve the test memory
echo "" | tee -a token-generation.log
echo "=== RETRIEVING TEST MEMORY ===" | tee -a token-generation.log

curl -s -X GET "http://localhost:8000/memory/list?memory_type=all&limit=5" \
  -H "Authorization: Bearer $TOKEN" \
  2>&1 | python3 -m json.tool | tee -a token-generation.log

# Final summary
echo "" | tee -a token-generation.log
echo "=== TASK 2 SUMMARY ===" | tee -a token-generation.log
echo "Token file: /root/jwt-token-only.txt" | tee -a token-generation.log
echo "Log file: /root/memory-deployment-audit/token-generation.log" | tee -a token-generation.log
