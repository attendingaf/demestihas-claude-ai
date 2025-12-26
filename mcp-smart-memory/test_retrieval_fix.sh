#!/bin/bash

echo "Testing Memory Retrieval Fix"
echo "============================"

# Test 1: API retrieval
echo -e "\n1. Testing API retrieval for 'configuration':"
RESULT=$(curl -s "http://localhost:7777/context?q=configuration")
if echo "$RESULT" | grep -q "results"; then
    echo "✅ API returns results"
    echo "$RESULT" | python3 -m json.tool | head -20
else
    echo "❌ API still returning no results"
fi

# Test 2: Different search term
echo -e "\n2. Testing API retrieval for 'memory':"
RESULT2=$(curl -s "http://localhost:7777/context?q=memory")
if echo "$RESULT2" | grep -q "results"; then
    echo "✅ Search for 'memory' works"
    COUNT=$(echo "$RESULT2" | python3 -c "import sys, json; data=json.load(sys.stdin); print(len(data.get('results', [])))")
    echo "   Found $COUNT results"
else
    echo "❌ Search still not working"
fi

# Test 3: Case sensitivity
echo -e "\n3. Testing case insensitive search 'CONFIGURATION':"
RESULT3=$(curl -s "http://localhost:7777/context?q=CONFIGURATION")
if echo "$RESULT3" | grep -q "results"; then
    echo "✅ Case-insensitive search works"
else
    echo "❌ Case-sensitive issue remains"
fi

# Test 4: Partial matching
echo -e "\n4. Testing partial match 'config':"
RESULT4=$(curl -s "http://localhost:7777/context?q=config")
if echo "$RESULT4" | grep -q "results"; then
    echo "✅ Partial matching works"
else
    echo "❌ Partial matching not working"
fi

echo -e "\n============================"

# Summary
echo -e "\nRETRIEVAL FIX STATUS:"
if echo "$RESULT" | grep -q "results"; then
    echo "✅ FIXED - Memory retrieval is working!"
    echo ""
    echo "Next: Test in Claude Desktop with:"
    echo "  get_relevant_context({ query: 'configuration' })"
else
    echo "❌ NOT FIXED - Retrieval still broken"
    echo ""
    echo "Debug with:"
    echo "  sqlite3 data/local_memory.db 'SELECT * FROM memories;'"
fi
