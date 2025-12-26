#!/bin/bash
# Test script for MiMerc agent

echo "🧪 Testing MiMerc Agent..."

# Test 1: Check if agent is running
echo "Test 1: Checking agent health..."
curl -s http://localhost:8002/health || echo "❌ Agent not responding on health endpoint"

# Test 2: Add item to list
echo -e "\nTest 2: Adding items to grocery list..."
curl -X POST http://localhost:8002/chat \
  -H "Content-Type: application/json" \
  -d '{
    "message": "Add milk, eggs, and bread to my grocery list",
    "thread_id": "test-family-list"
  }' | python -m json.tool

# Test 3: View list
echo -e "\nTest 3: Viewing grocery list..."
curl -X POST http://localhost:8002/chat \
  -H "Content-Type: application/json" \
  -d '{
    "message": "What is on my grocery list?",
    "thread_id": "test-family-list"
  }' | python -m json.tool

# Test 4: Check database tables
echo -e "\nTest 4: Checking database tables..."
docker exec mimerc-postgres psql -U mimerc -d mimerc_db -c "\dt" 2>/dev/null | grep checkpoint

echo -e "\n✅ Tests complete!"
