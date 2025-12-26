# EA-AI Tools Fix - Restart Instructions
*Generated: September 15, 2025 at 11:10 AM EDT*

## ✅ FIX APPLIED
The configuration has been updated to point to the correct MCP server location.

## 🚀 RESTART INSTRUCTIONS

### Step 1: Install Dependencies (if needed)
```bash
cd ~/Projects/demestihas-ai
npm install @modelcontextprotocol/sdk
```

### Step 2: Verify MCP Server Works
```bash
# Test the MCP server directly
node ~/Projects/demestihas-ai/mcp-server.js
# Press Ctrl+C after seeing "EA-AI MCP Server running"
```

### Step 3: Restart Claude Desktop
1. **Completely quit Claude Desktop** (not just close the window)
   - Right-click Claude icon in dock → Quit
   - OR: Claude menu → Quit Claude Desktop
   
2. **Wait 5 seconds**

3. **Reopen Claude Desktop**

### Step 4: Test EA-AI Tools
After restart, test these commands in a new conversation:

```
# Test 1: Check time (should work immediately)
Use osascript to check the current time

# Test 2: Memory access
Use ea_ai_memory to get session_state

# Test 3: Route to agent
Use ea_ai_route to route "check my calendar" to the appropriate agent

# Test 4: ADHD task breakdown
Use ea_ai_task_adhd to break down "prepare quarterly report" into 15-minute chunks

# Test 5: Calendar check
Use ea_ai_calendar_check to check for conflicts
```

## 📊 VERIFICATION CHECKLIST

After restart, you should be able to:
- [ ] See "EA-AI Bootstrap completed" in Claude logs (if visible)
- [ ] Use ea_ai_memory commands
- [ ] Use ea_ai_route commands
- [ ] Use ea_ai_family commands
- [ ] Use ea_ai_calendar_check commands
- [ ] Use ea_ai_task_adhd commands

## ⚠️ TROUBLESHOOTING

If tools still don't work after restart:

1. **Check the config was saved:**
```bash
cat ~/Library/Application\ Support/Claude/claude_desktop_config.json | grep ea-ai -A 3
```
Should show: `/Users/menedemestihas/Projects/demestihas-ai/mcp-server.js`

2. **Check Node.js is available:**
```bash
/Users/menedemestihas/.nvm/versions/node/v22.17.1/bin/node --version
```

3. **Test the MCP server directly:**
```bash
cd ~/Projects/demestihas-ai
/Users/menedemestihas/.nvm/versions/node/v22.17.1/bin/node mcp-server.js
```

4. **Check for errors in Claude logs:**
- Open Console.app
- Search for "Claude" or "ea-ai"
- Look for error messages

## 🎯 WHAT WAS FIXED

**Problem:** EA-AI tools were pointing to non-existent path
- ❌ Old: `/Users/menedemestihas/Projects/claude-desktop-ea-ai/mcp-server-v2.js`
- ✅ New: `/Users/menedemestihas/Projects/demestihas-ai/mcp-server.js`

**Impact:** All 5 EA-AI tools were unavailable
**Resolution:** Updated claude_desktop_config.json with correct path

## 📝 NEXT STEPS

Once EA-AI tools are verified working:
1. Test the integration with Google Calendar
2. Store important patterns in memory
3. Set up ADHD task optimization workflows
4. Configure family member personalizations

---
*Keep this document for reference if issues recur*
