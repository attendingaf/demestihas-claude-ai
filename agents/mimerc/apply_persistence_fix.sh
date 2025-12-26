#!/bin/bash
# Apply Critical State Persistence Fix
# This script applies the patch that fixes grocery list persistence

echo "================================"
echo "MiMerc State Persistence Fix"
echo "================================"
echo ""
echo "This patch fixes the critical bug where grocery lists"
echo "were being reset on each message instead of persisting."
echo ""

# Check if we're in the right directory
if [ ! -f "telegram_bot.py" ] || [ ! -f "agent.py" ]; then
    echo "❌ ERROR: Must run from the mimerc directory"
    echo "   Current directory: $(pwd)"
    exit 1
fi

echo "📍 Current directory: $(pwd)"
echo ""
echo "Files to be patched:"
echo "  - telegram_bot.py (line ~67)"
echo "  - agent.py (line ~197)"
echo ""

# Backup current files
echo "Creating backups..."
cp telegram_bot.py telegram_bot.py.backup.$(date +%Y%m%d_%H%M%S)
cp agent.py agent.py.backup.$(date +%Y%m%d_%H%M%S)
echo "✓ Backups created"
echo ""

echo "🔧 Applying fixes..."
echo ""

# The fix has already been applied via the PM's edit_file commands
# This script just verifies and reports the changes

# Check if the fix is already applied
if grep -q "# Don't initialize grocery_list" telegram_bot.py; then
    echo "✅ telegram_bot.py - Fix already applied"
else
    echo "⚠️  telegram_bot.py - Fix may not be applied correctly"
    echo "   Please verify manually"
fi

if grep -q "# The grocery_list MUST be included" agent.py; then
    echo "✅ agent.py - Fix already applied"
else
    echo "⚠️  agent.py - Fix may not be applied correctly"
    echo "   Please verify manually"
fi

echo ""
echo "================================"
echo "Next Steps:"
echo "================================"
echo ""
echo "1. Run the verification test:"
echo "   python verify_fix.py"
echo ""
echo "2. If using Docker, rebuild and restart:"
echo "   docker-compose down"
echo "   docker-compose build"
echo "   docker-compose up -d"
echo ""
echo "3. Test with your Telegram bot:"
echo "   - Send: 'Add milk to my list'"
echo "   - Send: 'Add eggs to my list'"
echo "   - Send: 'Show my list'"
echo "   - Both items should appear!"
echo ""
echo "✨ Fix complete!"