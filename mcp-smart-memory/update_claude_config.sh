#!/bin/bash

echo "Updating Claude Desktop Configuration"
echo "====================================="

CONFIG_DIR="$HOME/Library/Application Support/Claude"
CONFIG_FILE="$CONFIG_DIR/claude_desktop_config.json"
BACKUP_FILE="$CONFIG_DIR/claude_desktop_config.backup.$(date +%Y%m%d_%H%M%S).json"
NEW_CONFIG="$CONFIG_DIR/claude_desktop_config_new.json"

# 1. Create backup
echo "1. Creating backup..."
cp "$CONFIG_FILE" "$BACKUP_FILE"
echo "   ✓ Backup saved to: $(basename "$BACKUP_FILE")"

# 2. Apply new configuration
echo -e "\n2. Applying new configuration..."
cp "$NEW_CONFIG" "$CONFIG_FILE"
echo "   ✓ Configuration updated"

# 3. Show the changes
echo -e "\n3. Configuration changes:"
echo "   Added 'alwaysAllow' for smart-memory tools:"
echo "   - analyze_for_memory"
echo "   - propose_memory" 
echo "   - confirm_and_store"
echo "   - detect_patterns_in_conversation"
echo "   - get_relevant_context"
echo "   - track_decision"
echo "   - remember_error_and_fix"
echo "   - session_summary"
echo "   - check_memory_conflicts"

echo -e "\n4. Next steps:"
echo "   • Quit Claude Desktop completely (Cmd+Q)"
echo "   • Reopen Claude Desktop"
echo "   • The memory tools should now work without 'Allow' prompts"

echo -e "\n5. To revert if needed:"
echo "   cp \"$BACKUP_FILE\" \"$CONFIG_FILE\""

echo -e "\n====================================="
echo "Configuration update complete!"
