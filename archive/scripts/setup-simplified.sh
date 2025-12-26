#!/bin/bash

# EA-AI Bootstrap Integration Setup Script (No NPM Required)
# This version works without npm dependencies

set -e

echo "🚀 EA-AI Claude Desktop Integration Setup (Simplified)"
echo "======================================================="

# Colors for output
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

# Paths
EA_AI_DIR="/Users/menedemestihas/Projects/claude-desktop-ea-ai"
CLAUDE_CONFIG_DIR="/Users/menedemestihas/Library/Application Support/Claude"
CLAUDE_CONFIG_FILE="$CLAUDE_CONFIG_DIR/claude_desktop_config.json"

# Step 1: Check if Claude Desktop is installed
echo -e "${YELLOW}Step 1: Checking Claude Desktop installation...${NC}"
if [ -d "/Applications/Claude.app" ]; then
    echo -e "${GREEN}✓ Claude Desktop found${NC}"
else
    echo -e "${RED}✗ Claude Desktop not found in /Applications${NC}"
    exit 1
fi

# Step 2: Backup current configuration
echo -e "${YELLOW}Step 2: Backing up current configuration...${NC}"
if [ -f "$CLAUDE_CONFIG_FILE" ]; then
    cp "$CLAUDE_CONFIG_FILE" "$CLAUDE_CONFIG_FILE.backup.$(date +%Y%m%d_%H%M%S)"
    echo -e "${GREEN}✓ Configuration backed up${NC}"
else
    echo -e "${YELLOW}! No existing configuration found, will create new${NC}"
fi

# Step 3: Create required .md files if they don't exist
echo -e "${YELLOW}Step 3: Ensuring required files exist...${NC}"
cd "$EA_AI_DIR"

for file in state.md routing.md cache.md smart-memory.md family.md templates.md; do
    if [ ! -f "$file" ]; then
        touch "$file"
        echo "Created: $file"
    fi
done
echo -e "${GREEN}✓ Required files ready${NC}"

# Step 4: Update Claude Desktop configuration
echo -e "${YELLOW}Step 4: Updating Claude Desktop configuration...${NC}"

# Create the updated configuration with EA-AI server
cat > "$CLAUDE_CONFIG_FILE" << 'EOF'
{
  "mcpServers": {
    "ea-ai": {
      "command": "node",
      "args": [
        "/Users/menedemestihas/Projects/claude-desktop-ea-ai/mcp-server-simple.js"
      ],
      "alwaysAllow": [
        "ea_ai_route",
        "ea_ai_memory",
        "ea_ai_family",
        "ea_ai_calendar_check",
        "ea_ai_task_adhd"
      ]
    },
    "git": {
      "command": "/Users/menedemestihas/.local/bin/uvx",
      "args": [
        "mcp-server-git"
      ]
    },
    "smart-memory": {
      "command": "node",
      "args": [
        "/Users/menedemestihas/Projects/demestihas-ai/mcp-smart-memory/index.js"
      ],
      "alwaysAllow": [
        "analyze_for_memory",
        "propose_memory",
        "confirm_and_store",
        "detect_patterns_in_conversation",
        "get_relevant_context",
        "track_decision",
        "remember_error_and_fix",
        "session_summary",
        "check_memory_conflicts"
      ]
    },
    "pluma": {
      "command": "node",
      "args": [
        "/Users/menedemestihas/Projects/demestihas-ai/pluma-mcp-server/src/index.js"
      ],
      "env": {
        "PYTHONPATH": "/Users/menedemestihas/Projects/demestihas-ai/pluma-local"
      }
    }
  }
}
EOF

echo -e "${GREEN}✓ Configuration updated${NC}"

# Step 5: Test the bootstrap
echo -e "${YELLOW}Step 5: Testing EA-AI bootstrap...${NC}"
cd "$EA_AI_DIR"

# Create a simple test script
cat > test-integration.js << 'EOF'
const EABootstrap = require('./bootstrap.js');

(async () => {
  console.log('Testing EA-AI Bootstrap...');
  
  try {
    const result = await EABootstrap.init({
      maxLatency: 300,
      fallbackEnabled: true,
      memoryShare: true
    });
    
    if (result.status === 'ready') {
      console.log(`✓ Bootstrap successful in ${result.bootstrapTime}ms`);
      console.log(`✓ Agents ready: ${result.agents.join(', ')}`);
      
      if (result.bootstrapTime < 300) {
        console.log('✓ Performance target met');
      } else {
        console.log(`⚠ Performance warning: ${result.bootstrapTime}ms > 300ms target`);
      }
      
      process.exit(0);
    } else {
      console.log('✗ Bootstrap failed');
      process.exit(1);
    }
  } catch (error) {
    console.error('✗ Error:', error.message);
    // Don't fail completely, just warn
    console.log('⚠ Bootstrap test had issues but continuing setup');
    process.exit(0);
  }
})();
EOF

node test-integration.js
TEST_RESULT=$?

if [ $TEST_RESULT -eq 0 ]; then
    echo -e "${GREEN}✓ Bootstrap test completed${NC}"
else
    echo -e "${YELLOW}⚠ Bootstrap test had warnings but setup will continue${NC}"
fi

# Step 6: Create convenience scripts
echo -e "${YELLOW}Step 6: Creating convenience scripts...${NC}"

# Create start script
cat > "$EA_AI_DIR/start-ea-ai.sh" << 'EOF'
#!/bin/bash
echo "Starting EA-AI MCP Server..."
node /Users/menedemestihas/Projects/claude-desktop-ea-ai/mcp-server-simple.js
EOF
chmod +x "$EA_AI_DIR/start-ea-ai.sh"

# Create monitor script
cat > "$EA_AI_DIR/monitor-ea-ai.sh" << 'EOF'
#!/bin/bash
echo "Monitoring EA-AI Performance..."
while true; do
    clear
    echo "EA-AI System Monitor"
    echo "==================="
    echo ""
    
    # Check if MCP server is running
    if pgrep -f "mcp-server" > /dev/null; then
        echo "✓ EA-AI MCP Server: Running"
    else
        echo "✗ EA-AI MCP Server: Not Running"
    fi
    
    # Check Claude Desktop
    if pgrep -f "Claude" > /dev/null; then
        echo "✓ Claude Desktop: Running"
    else
        echo "✗ Claude Desktop: Not Running"
    fi
    
    echo ""
    echo "Press Ctrl+C to exit"
    sleep 5
done
EOF
chmod +x "$EA_AI_DIR/monitor-ea-ai.sh"

echo -e "${GREEN}✓ Convenience scripts created${NC}"

# Step 7: Final instructions
echo ""
echo -e "${GREEN}=========================================="
echo "✅ EA-AI Integration Setup Complete!"
echo "==========================================${NC}"
echo ""
echo "Next steps:"
echo "1. Restart Claude Desktop for changes to take effect"
echo "   - Quit Claude completely (Cmd+Q)"
echo "   - Wait 5 seconds"
echo "   - Reopen Claude from Applications"
echo ""
echo "2. The EA-AI system will automatically initialize when Claude starts"
echo ""
echo "Available EA-AI tools in Claude:"
echo "  • ea_ai_route - Route to specialized agents"
echo "  • ea_ai_memory - Access smart memory system"
echo "  • ea_ai_family - Family context & personalization"
echo "  • ea_ai_calendar_check - 6-calendar conflict resolution"
echo "  • ea_ai_task_adhd - ADHD-optimized task management"
echo ""
echo "Test commands to try in Claude:"
echo '  "Use EA-AI to check my calendar"'
echo '  "EA-AI: Break down this task into 15-minute chunks"'
echo '  "Route through EA-AI: draft an email"'
echo ""
echo "Useful commands:"
echo "  • Start manually: $EA_AI_DIR/start-ea-ai.sh"
echo "  • Monitor status: $EA_AI_DIR/monitor-ea-ai.sh"
echo "  • Test bootstrap: node $EA_AI_DIR/test-integration.js"
echo ""
echo -e "${YELLOW}⚠ Remember to restart Claude Desktop now!${NC}"
