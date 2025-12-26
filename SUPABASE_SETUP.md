# 🚀 Supabase Cloud Sync Setup Guide
*Last Updated: January 14, 2025*

## Step 1: Apply Database Schema Fix

### ⚠️ Memory Limit Issue?
If you get error `memory required is 61 MB, maintenance_work_mem is 32 MB`, use one of these solutions:

### Option A: Memory-Optimized Version (Try First)
1. Open your Supabase project dashboard:
   ```
   https://supabase.com/dashboard/project/oletgdpevhdxbywrqeyh
   ```

2. Navigate to **SQL Editor** (left sidebar)

3. Click **New Query**

4. Copy the ENTIRE contents of:
   ```
   /Users/menedemestihas/Projects/demestihas-ai/supabase-fix-optimized.sql
   ```

5. Paste and click **Run**

### Option B: Minimal Version (If Option A Fails)
If you still get memory errors:

1. Use the minimal version instead:
   ```
   /Users/menedemestihas/Projects/demestihas-ai/supabase-fix-minimal.sql
   ```

2. This skips indexes but still enables cloud sync

3. Performance will be fine for <1000 memories

### Success Indicators
You should see:
- "✅ Ready for cloud sync!" or
- "✅ SUCCESS: Embedding column added!"

### If Both Fail
1. Run each command separately (copy one at a time)
2. Start with just the ALTER TABLE command:
   ```sql
   ALTER TABLE project_memories 
   ADD COLUMN IF NOT EXISTS embedding vector(1536);
   ```

## Step 2: Start MCP Server

**Option A: Use the start script (Recommended)**
```bash
/Users/menedemestihas/Projects/demestihas-ai/start-memory-server.sh
```

**Option B: Manual start**
```bash
# Kill any existing processes
lsof -ti:7777 | xargs kill -9 2>/dev/null
lsof -ti:7778 | xargs kill -9 2>/dev/null

# Navigate to MCP directory
cd /Users/menedemestihas/Projects/demestihas-ai/mcp-smart-memory

# Start the server
npm run api
```

Wait for the message: `[API] Server running on http://localhost:7777`

## Step 3: Test Cloud Sync

In a new terminal window:

```bash
# Make test script executable
chmod +x /Users/menedemestihas/Projects/demestihas-ai/test-supabase.sh

# Run the test
/Users/menedemestihas/Projects/demestihas-ai/test-supabase.sh
```

## Step 4: Verify Success

Check for these indicators:

### ✅ Success Signs:
- Health check shows `"cloudStatus": "connected"`
- Cloud memories count > 0
- No error messages in server logs
- Semantic search returns results with scores

### ❌ If Issues Occur:

**Issue: "relation 'project_memories' does not exist"**
- The table wasn't created properly
- Re-run the SQL script in Supabase

**Issue: "cloudStatus: disconnected"**
- Check .env file has correct credentials
- Verify Supabase project is unpaused
- Check network connectivity

**Issue: "embedding column does not exist"**
- The ALTER TABLE didn't work
- Try creating a new table with embedding column

## Step 5: Migrate Local Memories to Cloud

Once connected, migrate your 48 existing memories:

```bash
# This will trigger batch sync of all local memories
curl -X POST http://localhost:7777/migrate-to-cloud
```

## Step 6: Monitor Cloud Sync

View real-time sync status:

```bash
# Watch sync progress (updates every 5 seconds)
watch -n 5 'curl -s http://localhost:7777/health | python3 -m json.tool | grep -E "(totalMemories|cloudStatus|lastSync)"'
```

## Troubleshooting Commands

```bash
# Check Supabase connection directly
curl -X GET "https://oletgdpevhdxbywrqeyh.supabase.co/rest/v1/project_memories?select=count" \
  -H "apikey: eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6Im9sZXRnZHBldmhkeGJ5d3JxZXloIiwicm9sZSI6ImFub24iLCJpYXQiOjE3NTcxMjU4MTYsImV4cCI6MjA3MjcwMTgxNn0.Mr3jgTBOfSRq3brhHpp9H-8S_eiugZj88LqZ4ohjVlk" \
  -H "Authorization: Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6Im9sZXRnZHBldmhkeGJ5d3JxZXloIiwicm9sZSI6ImFub24iLCJpYXQiOjE3NTcxMjU4MTYsImV4cCI6MjA3MjcwMTgxNn0.Mr3jgTBOfSRq3brhHpp9H-8S_eiugZj88LqZ4ohjVlk"

# Check MCP server logs
tail -f /Users/menedemestihas/Projects/demestihas-ai/claude-desktop-rag/rag.log

# Test OpenAI embeddings
curl -X POST http://localhost:7777/test-embedding \
  -H "Content-Type: application/json" \
  -d '{"text": "test embedding generation"}'
```

## Expected Outcome

After successful setup:
1. **Local Storage**: SQLite continues working (48 memories)
2. **Cloud Backup**: All memories synced to Supabase
3. **Semantic Search**: Uses OpenAI embeddings for similarity
4. **Cross-Device**: Access memories from any device
5. **Performance**: <100ms retrieval with cloud fallback

## Next Steps

Once cloud sync is verified:
1. Return to this chat
2. Confirm: "Supabase cloud sync working"
3. We'll proceed with Calendar Conflict Detection

---

**Important**: Keep the MCP server running during setup. The cloud sync happens automatically every 30 seconds once connected.
