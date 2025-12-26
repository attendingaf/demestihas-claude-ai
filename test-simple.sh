#!/bin/bash
# Test without embeddings to isolate issue

echo "Testing storage without embeddings..."

# Store a simple memory
curl -X POST http://localhost:7777/store \
  -H "Content-Type: application/json" \
  -d '{
    "content": "Test memory without embedding: Calendar conflicts detected",
    "type": "note",
    "importance": "low"
  }' | python3 -m json.tool

echo ""
echo "Checking count..."
curl -s http://localhost:7777/health | python3 -c "
import json, sys
data = json.load(sys.stdin)
print(f\"Total memories: {data['stats']['totalMemories']}\")
print(f\"Cloud status: {data['stats']['cloudStatus']}\")
"

echo ""
echo "Checking OpenAI API key..."
if grep -q "sk-proj" /Users/menedemestihas/Projects/demestihas-ai/claude-desktop-rag/.env; then
    echo "✅ OpenAI API key found in .env"
else
    echo "❌ OpenAI API key missing or invalid"
fi
