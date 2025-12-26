#!/bin/bash
# Simple check to see current state and guide manual editing

echo "📍 Quick Yanay.py Import Guide"
echo "=============================="
echo ""

ssh root@178.156.170.161 << 'ENDSSH'
cd /root/demestihas-ai

echo "Current imports in yanay.py:"
echo "----------------------------"
echo ""

# Show all import lines with line numbers
echo "📝 All import statements:"
grep -n "^import\|^from" yanay.py | head -15

echo ""
echo "🎯 The RIGHT place to add new imports:"
echo "--------------------------------------"

# Find the last import line
LAST_IMPORT=$(grep -n "^import\|^from" yanay.py | tail -1)
LAST_LINE_NUM=$(echo $LAST_IMPORT | cut -d: -f1)

echo "Last import is: $LAST_IMPORT"
echo ""
echo "ADD YOUR IMPORTS AFTER LINE $LAST_LINE_NUM"
echo ""
echo "Here's what to add (copy this exactly):"
echo "========================================="
cat << 'IMPORTS'

# Conversation Enhancement
try:
    from conversation_manager import ConversationStateManager
    from token_manager import TokenBudgetManager
    print('Enhancement modules imported')
except ImportError:
    ConversationStateManager = None
    TokenBudgetManager = None
IMPORTS
echo "========================================="
echo ""
echo "📝 Steps for nano:"
echo "1. nano yanay.py"
echo "2. Press Ctrl+_ (underscore) to go to line"
echo "3. Enter: $LAST_LINE_NUM"
echo "4. Press Enter to go to that line"
echo "5. Press End key to go to end of line"
echo "6. Press Enter to create new line"
echo "7. Paste the imports above"
echo "8. Press Ctrl+X, then Y, then Enter to save"
echo ""
echo "Or use this simple command to do it automatically:"
echo "sed -i '${LAST_LINE_NUM}a\\
\\
# Conversation Enhancement\\
try:\\
    from conversation_manager import ConversationStateManager\\
    from token_manager import TokenBudgetManager\\
    print(\"Enhancement modules imported\")\\
except ImportError:\\
    ConversationStateManager = None\\
    TokenBudgetManager = None' yanay.py"

ENDSSH
