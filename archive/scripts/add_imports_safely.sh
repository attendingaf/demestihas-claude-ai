#!/bin/bash
# Safe import addition script - shows exactly where to add the lines

echo "🔍 Finding the right place to add imports in yanay.py"
echo "===================================================="
echo ""

ssh root@178.156.170.161 << 'ENDSSH'
cd /root/demestihas-ai

echo "1️⃣ Creating backup first..."
cp yanay.py yanay.py.backup.$(date +%Y%m%d_%H%M%S)

echo ""
echo "2️⃣ Showing current imports in yanay.py:"
echo "----------------------------------------"
# Show the first 30 lines which should contain imports
head -30 yanay.py | grep -n "^import\|^from" | head -10

echo ""
echo "3️⃣ Finding the last import line number:"
# Find the line number of the last import
LAST_IMPORT=$(grep -n "^import\|^from" yanay.py | tail -1 | cut -d: -f1)
echo "Last import is at line: $LAST_IMPORT"

echo ""
echo "4️⃣ Showing context around line $LAST_IMPORT:"
echo "----------------------------------------"
# Show 5 lines before and after the last import
sed -n "$((LAST_IMPORT-2)),$((LAST_IMPORT+5))p" yanay.py | cat -n

echo ""
echo "5️⃣ Adding imports automatically after line $LAST_IMPORT..."
# Use sed to add the imports after the last import line
sed -i "${LAST_IMPORT}a\\
\\
# Conversation Enhancement Imports\\
try:\\
    from conversation_manager import ConversationStateManager\\
    from token_manager import TokenBudgetManager\\
    print('✅ Enhancement modules imported')\\
except ImportError as e:\\
    print(f'⚠️ Enhancement modules not available: {e}')\\
    ConversationStateManager = None\\
    TokenBudgetManager = None" yanay.py

echo "✅ Imports added!"

echo ""
echo "6️⃣ Verifying the changes:"
echo "-------------------------"
# Show the area where we added the imports
sed -n "$((LAST_IMPORT)),$((LAST_IMPORT+10))p" yanay.py | cat -n

echo ""
echo "7️⃣ Testing syntax..."
python3 -m py_compile yanay.py 2>&1 && echo "✅ Syntax is valid!" || echo "❌ Syntax error detected"

echo ""
echo "8️⃣ Checking if managers can be imported:"
python3 -c "
import sys
sys.path.append('/root/demestihas-ai')
try:
    from conversation_manager import ConversationStateManager
    from token_manager import TokenBudgetManager
    print('✅ Both managers import successfully!')
except Exception as e:
    print(f'❌ Import error: {e}')
"

echo ""
echo "📝 Next step: Initialize the managers in __init__ method"
echo "========================================================="
echo ""
echo "Now we need to find the __init__ method and add initialization."
echo "Searching for __init__ method..."

# Find the __init__ method
INIT_LINE=$(grep -n "def __init__" yanay.py | head -1 | cut -d: -f1)
if [ ! -z "$INIT_LINE" ]; then
    echo "Found __init__ at line $INIT_LINE"
    echo ""
    echo "Showing __init__ method (first 20 lines):"
    sed -n "${INIT_LINE},$((INIT_LINE+20))p" yanay.py | cat -n
    
    echo ""
    echo "To add initialization, look for lines with 'self.' assignments"
    echo "and add these lines after them:"
    echo ""
    echo "        # Initialize conversation enhancement"
    echo "        try:"
    echo "            self.conversation_manager = ConversationStateManager() if ConversationStateManager else None"
    echo "            self.token_manager = TokenBudgetManager() if TokenBudgetManager else None"
    echo "            if self.conversation_manager:"
    echo "                print('✅ Conversation enhancement initialized')"
    echo "        except Exception as e:"
    echo "            print(f'⚠️ Enhancement initialization failed: {e}')"
    echo "            self.conversation_manager = None"
    echo "            self.token_manager = None"
else
    echo "Could not find __init__ method automatically"
fi

ENDSSH

echo ""
echo "✅ Imports have been added automatically!"
echo ""
echo "📋 To complete the setup:"
echo "1. Check if syntax is valid (shown above)"
echo "2. If valid, restart Yanay: docker-compose restart yanay"
echo "3. If not valid, restore backup: cp yanay.py.backup.[TAB] yanay.py"
