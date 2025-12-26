#!/bin/bash

echo "Debugging Memory Retrieval Issue"
echo "================================"

# Check database content directly
echo -e "\nDatabase Content Check:"
sqlite3 ~/Projects/demestihas-ai/mcp-smart-memory/data/local_memory.db \
  "SELECT COUNT(*) as total_memories FROM memories;" 2>/dev/null || echo "Table 'memories' not found"

# Check table structure
echo -e "\nTable Structure:"
sqlite3 ~/Projects/demestihas-ai/mcp-smart-memory/data/local_memory.db \
  ".schema" 2>/dev/null || echo "No tables found"

# List all tables
echo -e "\nAll Tables:"
sqlite3 ~/Projects/demestihas-ai/mcp-smart-memory/data/local_memory.db \
  ".tables" 2>/dev/null || echo "Database empty"

# Try to query any existing data
echo -e "\nSample Data (first 3 records):"
sqlite3 ~/Projects/demestihas-ai/mcp-smart-memory/data/local_memory.db \
  "SELECT * FROM memories LIMIT 3;" 2>/dev/null || \
  sqlite3 ~/Projects/demestihas-ai/mcp-smart-memory/data/local_memory.db \
  "SELECT name FROM sqlite_master WHERE type='table';" 2>/dev/null || \
  echo "Unable to query database"

echo -e "\n================================"
echo "Diagnosis complete"
