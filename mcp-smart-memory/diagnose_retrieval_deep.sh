#!/bin/bash

echo "=== Memory Retrieval Deep Diagnosis ==="
echo "Date: $(date)"
echo ""

# Check database
echo "1. DATABASE CHECK:"
echo "-----------------"
DB_PATH="data/smart_memory.db"

if [ -f "$DB_PATH" ]; then
    echo "✅ Database exists at: $DB_PATH"
    echo "Size: $(ls -lh $DB_PATH | awk '{print $5}')"
    echo ""
    
    echo "2. MEMORY COUNT:"
    echo "----------------"
    sqlite3 "$DB_PATH" "SELECT COUNT(*) as count FROM memories;" 2>/dev/null || echo "❌ Error counting memories"
    echo ""
    
    echo "3. SAMPLE MEMORIES (first 3):"
    echo "------------------------------"
    sqlite3 "$DB_PATH" "SELECT id, substr(content, 1, 50) as content_preview, type, category FROM memories LIMIT 3;" 2>/dev/null || echo "❌ Error reading memories"
    echo ""
    
    echo "4. FTS TABLE CHECK:"
    echo "-------------------"
    sqlite3 "$DB_PATH" "SELECT COUNT(*) as fts_count FROM memories_fts;" 2>/dev/null || echo "❌ FTS table missing or empty"
    echo ""
    
    echo "5. SEARCH TEST - Direct FTS Query:"
    echo "-----------------------------------"
    echo "Searching for 'calendar':"
    sqlite3 "$DB_PATH" "SELECT id, substr(content, 1, 100) FROM memories WHERE content LIKE '%calendar%';" 2>/dev/null || echo "No results"
    echo ""
    
    echo "6. FTS5 MATCH Test:"
    echo "-------------------"
    echo "Testing FTS5 match for 'calendar':"
    sqlite3 "$DB_PATH" "SELECT m.id, substr(m.content, 1, 100) FROM memories m JOIN memories_fts ON m.rowid = memories_fts.rowid WHERE memories_fts MATCH 'calendar';" 2>/dev/null || echo "No FTS results"
    echo ""
    
    echo "7. All Memory Content (to find patterns):"
    echo "------------------------------------------"
    sqlite3 "$DB_PATH" "SELECT id, content FROM memories;" 2>/dev/null || echo "❌ Could not retrieve content"
    echo ""
    
else
    echo "❌ Database not found at $DB_PATH"
fi

echo "8. API TEST:"
echo "------------"
# Test the API
echo "Testing /health endpoint:"
curl -s http://localhost:7777/health | jq '.' 2>/dev/null || echo "❌ API not responding"
echo ""

echo "Testing /context endpoint with 'calendar':"
curl -s "http://localhost:7777/context?q=calendar&limit=5" | jq '.' 2>/dev/null || echo "❌ Context endpoint failed"
echo ""

echo "9. MEMORY CONTENT ANALYSIS:"
echo "----------------------------"
echo "Searching for any memory containing 'cal' or 'Cal':"
sqlite3 "$DB_PATH" "SELECT id, content FROM memories WHERE content LIKE '%cal%' OR content LIKE '%Cal%';" 2>/dev/null || echo "No matches"
echo ""

echo "=== End Diagnosis ==="
