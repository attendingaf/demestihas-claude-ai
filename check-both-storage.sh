#!/bin/bash
# Direct SQLite inspection

DB="/Users/menedemestihas/Projects/demestihas-ai/mcp-smart-memory/data/local_memory.db"

echo "📊 SQLite Database Contents"
echo "==========================="
echo ""
echo "Memories in LOCAL storage (SQLite):"
sqlite3 "$DB" "SELECT id, substr(content, 1, 50) as content_preview, interaction_type FROM project_memories_cache;" 2>/dev/null

echo ""
echo "Total count: $(sqlite3 "$DB" 'SELECT COUNT(*) FROM project_memories_cache;' 2>/dev/null)"

echo ""
echo "==========================="
echo "Checking Supabase (CLOUD storage):"
curl -s "https://oletgdpevhdxbywrqeyh.supabase.co/rest/v1/project_memories?select=id,content&limit=5" \
  -H "apikey: eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6Im9sZXRnZHBldmhkeGJ5d3JxZXloIiwicm9sZSI6ImFub24iLCJpYXQiOjE3NTcxMjU4MTYsImV4cCI6MjA3MjcwMTgxNn0.Mr3jgTBOfSRq3brhHpp9H-8S_eiugZj88LqZ4ohjVlk" \
  | python3 -m json.tool

echo ""
echo "Summary:"
echo "- SQLite = Local fast storage (on your Mac)"
echo "- Supabase = Cloud backup (PostgreSQL online)"
echo "- They should sync but currently aren't"
