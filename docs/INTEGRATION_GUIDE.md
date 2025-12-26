# EA-AI Claude Desktop Integration Guide

## Quick Start (Automated)

Run this single command in Terminal:
```bash
cd /Users/menedemestihas/Projects/claude-desktop-ea-ai && chmod +x setup-integration.sh && ./setup-integration.sh
```

This will automatically:
– Install dependencies
– Backup your current Claude config
– Integrate EA-AI with Claude Desktop
– Test the bootstrap system
– Create convenience scripts

Then restart Claude Desktop.

## Manual Step-by-Step Instructions

### Step 1: Prepare the EA-AI System

Open Terminal and navigate to the EA-AI directory:
```bash
cd /Users/menedemestihas/Projects/claude-desktop-ea-ai
```

### Step 2: Install Dependencies

Install the MCP SDK required for Claude integration:
```bash
npm install @modelcontextprotocol/sdk
```

### Step 3: Backup Current Configuration

Save your current Claude Desktop configuration:
```bash
cp "/Users/menedemestihas/Library/Application Support/Claude/claude_desktop_config.json" \
   "/Users/menedemestihas/Library/Application Support/Claude/claude_desktop_config.backup.$(date +%Y%m%d_%H%M%S).json"
```

### Step 4: Update Claude Configuration

Edit the Claude Desktop configuration file:
```bash
nano "/Users/menedemestihas/Library/Application Support/Claude/claude_desktop_config.json"
```

Add the EA-AI server to the `mcpServers` section:
```json
{
  "mcpServers": {
    "ea-ai": {
      "command": "node",
      "args": [
        "/Users/menedemestihas/Projects/claude-desktop-ea-ai/mcp-server.js"
      ],
      "alwaysAllow": [
        "ea_ai_route",
        "ea_ai_memory",
        "ea_ai_family",
        "ea_ai_calendar_check",
        "ea_ai_task_adhd"
      ]
    },
    // ... keep your other servers ...
  }
}
```

### Step 5: Test the Bootstrap

Verify the bootstrap system works:
```bash
node -e "const EA = require('./bootstrap.js'); EA.init().then(r => console.log('Success:', r.bootstrapTime + 'ms'));"
```

You should see: `Success: [time]ms` (should be under 300ms)

### Step 6: Restart Claude Desktop

1. Quit Claude Desktop completely (Cmd+Q)
2. Wait 5 seconds
3. Reopen Claude Desktop from Applications

### Step 7: Verify Integration

In Claude Desktop, you can now use these commands:

**Test EA-AI routing:**
"Route this through EA-AI: check my calendar for conflicts"

**Test smart memory:**
"Use EA-AI memory to remember this: I prefer 15-minute task chunks"

**Test family context:**
"EA-AI: What are my family member preferences?"

## Available EA-AI Tools

Once integrated, Claude has access to:

### 1. Agent Routing (`ea_ai_route`)
Routes requests to specialized agents:
– **Pluma**: Email operations
– **Huata**: Calendar intelligence  
– **Lyco**: Task management
– **Kairos**: Time management

### 2. Smart Memory (`ea_ai_memory`)
– Store patterns and preferences
– Retrieve context across sessions
– Search memory contents
– Persist important information

### 3. Family Context (`ea_ai_family`)
– Personalization for each family member
– ADHD adaptations (Eight + Six types)
– Context-aware responses

### 4. Calendar Intelligence (`ea_ai_calendar_check`)
Manages 6 calendars simultaneously:
– Primary (menelaos4@gmail.com)
– Beltline (mene@beltlineconsulting.co)
– LyS Familia
– Limon y Sal
– Cindy's calendar
– Au Pair schedule

### 5. ADHD Task Management (`ea_ai_task_adhd`)
– Break tasks into 15-minute chunks
– Energy-level matching
– Priority quadrants
– Time blocking

## Troubleshooting

### Issue: Bootstrap takes longer than 300ms

**Solution**: Check that all .md files exist in the EA-AI directory:
```bash
ls -la /Users/menedemestihas/Projects/claude-desktop-ea-ai/*.md
```

If missing, create them:
```bash
touch state.md routing.md cache.md smart-memory.md family.md templates.md
```

### Issue: Claude doesn't recognize EA-AI tools

**Solution**: Verify the configuration was saved correctly:
```bash
cat "/Users/menedemestihas/Library/Application Support/Claude/claude_desktop_config.json" | grep ea-ai
```

If not present, manually edit the file again.

### Issue: MCP server won't start

**Solution**: Check Node.js is installed:
```bash
node --version
```

Should show v16 or higher. If not, install Node.js from nodejs.org

### Issue: Permission denied errors

**Solution**: Fix permissions:
```bash
chmod +x /Users/menedemestihas/Projects/claude-desktop-ea-ai/*.sh
chmod 644 /Users/menedemestihas/Projects/claude-desktop-ea-ai/*.js
```

## Performance Monitoring

Check EA-AI performance:
```bash
/Users/menedemestihas/Projects/claude-desktop-ea-ai/monitor-ea-ai.sh
```

View logs:
```bash
tail -f /Users/menedemestihas/Projects/claude-desktop-ea-ai/execution.log
```

## Rollback Instructions

If you need to remove EA-AI integration:

1. Restore original configuration:
```bash
cp "/Users/menedemestihas/Library/Application Support/Claude/claude_desktop_config.backup."* \
   "/Users/menedemestihas/Library/Application Support/Claude/claude_desktop_config.json"
```

2. Restart Claude Desktop

## Advanced Configuration

### Adjusting Bootstrap Timeout

Edit `/Users/menedemestihas/Projects/claude-desktop-ea-ai/bootstrap.js`:

```javascript
// Change line 30 from:
maxLatency: 300,
// To:
maxLatency: 500, // Allow 500ms for slower systems
```

### Adding Custom Agents

Edit `/Users/menedemestihas/Projects/claude-desktop-ea-ai/mcp-server.js` and add to the tools array:

```javascript
{
  name: 'ea_ai_custom',
  description: 'Your custom tool',
  inputSchema: {
    // Your schema
  }
}
```

## Support

For issues, check:
– Execution log: `execution.log`
– Test bootstrap: `node test-integration.js`
– Monitor status: `./monitor-ea-ai.sh`

## Success Indicators

You'll know EA-AI is working when:
– Claude remembers context between sessions
– Tasks are automatically broken into 15-minute chunks
– Calendar conflicts are detected across all 6 calendars
– Family member preferences are applied automatically
– Bootstrap completes in <300ms
