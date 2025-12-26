#!/bin/bash

echo "Memory Retrieval Diagnostic"
echo "==========================="

cd ~/Projects/demestihas-ai/mcp-smart-memory

echo -e "\n1. Database Contents:"
sqlite3 data/local_memory.db "SELECT COUNT(*) as count FROM memories;" 2>/dev/null || echo "No memories table"

echo -e "\n2. Sample Memory:"
sqlite3 data/local_memory.db "SELECT id, category, content FROM memories LIMIT 1;" 2>/dev/null || echo "Cannot read memories"

echo -e "\n3. Table Schema:"
sqlite3 data/local_memory.db ".schema memories" 2>/dev/null || echo "No schema found"

echo -e "\n4. Search Test via API:"
curl -s "http://localhost:7777/context?q=configuration" | python3 -m json.tool 2>/dev/null || echo "API error"

echo -e "\n5. Files to examine:"
echo "   - index.js (get_relevant_context function)"
echo "   - memory-api.js (GET /context endpoint)"
echo "   - Any SQL query builders or search functions"

echo -e "\n==========================="
echo "Run 'claude-code ~/Projects/demestihas-ai/mcp-smart-memory' to fix"
