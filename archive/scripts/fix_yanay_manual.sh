#!/bin/bash
# Manual integration fix for Yanay enhancement

echo "🔧 Manual Yanay Enhancement Integration"
echo "======================================"
echo ""

ssh root@178.156.170.161 << 'ENDSSH'
cd /root/demestihas-ai

echo "1️⃣ Fixing Telegram conflict..."
# Kill any stray Python processes
pkill -f "python.*yanay" 2>/dev/null || true
pkill -f "python.*bot" 2>/dev/null || true
sleep 2

echo "2️⃣ Creating clean enhancement patch..."
cat > yanay_enhancement_simple.py << 'PATCH'
# Add these imports at the top of yanay.py
IMPORTS_TO_ADD = """
from conversation_manager import ConversationStateManager
from token_manager import TokenBudgetManager
try:
    from anthropic import Anthropic
except ImportError:
    Anthropic = None
"""

# Add to __init__ method after other self. assignments
INIT_TO_ADD = """
        # Conversation Enhancement
        try:
            self.conversation_manager = ConversationStateManager()
            self.token_manager = TokenBudgetManager()
            if Anthropic:
                opus_key = os.getenv("ANTHROPIC_OPUS_KEY", os.getenv("ANTHROPIC_API_KEY"))
                self.opus_client = Anthropic(api_key=opus_key) if opus_key else None
            else:
                self.opus_client = None
            print("✅ Conversation enhancement initialized")
        except Exception as e:
            print(f"⚠️ Enhancement init warning: {e}")
            self.conversation_manager = None
            self.token_manager = None
            self.opus_client = None
"""

# Add these methods to the class
METHODS_TO_ADD = """
    def evaluate_response_mode(self, message, user_id, username=None):
        '''Simple routing decision'''
        message_lower = message.lower()
        
        # Emotional keywords
        if any(word in message_lower for word in ['stress', 'worried', 'anxious', 'sad']):
            return {"mode": "conversation", "reason": "emotional"}
        
        # Educational queries
        if message_lower.startswith(('why', 'how', 'what is')):
            return {"mode": "conversation", "reason": "educational"}
        
        # Direct calendar tasks
        if any(word in message_lower for word in ['appointment', 'meeting', 'calendar']):
            return {"mode": "delegation", "agent": "huata"}
        
        # Task management
        if any(word in message_lower for word in ['task', 'todo', 'remind']):
            return {"mode": "delegation", "agent": "lyco"}
        
        return {"mode": "delegation", "agent": "lyco"}

    def opus_conversation(self, message, user_id, username=None):
        '''Opus conversation handler'''
        if not self.opus_client:
            return None
        
        try:
            # Simple conversation without async
            prompt = f"You are Yanay, a helpful AI assistant. Respond warmly to: {message}"
            
            response = self.opus_client.messages.create(
                model="claude-3-sonnet-20240229",  # Use Sonnet for now
                max_tokens=500,
                messages=[{"role": "user", "content": prompt}]
            )
            
            response_text = response.content[0].text
            
            # Track conversation
            if self.conversation_manager:
                self.conversation_manager.add_turn(user_id, message, response_text)
            
            return response_text
        except Exception as e:
            print(f"Opus error: {e}")
            return None
"""
PATCH

echo "3️⃣ Applying manual fix to yanay.py..."
# Backup current
cp yanay.py yanay.py.backup.$(date +%Y%m%d_%H%M%S)

# First, check if we can parse the file
python3 -c "
with open('yanay.py', 'r') as f:
    content = f.read()
print('✅ File readable')
"

# Apply simple fixes manually
python3 << 'PYTHON'
import os

# Read the file
with open('yanay.py', 'r') as f:
    lines = f.readlines()

# Add imports if not present
if not any('conversation_manager' in line for line in lines):
    # Find where to add imports (after last import)
    import_idx = 0
    for i, line in enumerate(lines):
        if line.startswith('import ') or line.startswith('from '):
            import_idx = i + 1
    
    # Add our imports
    lines.insert(import_idx, '\n# Conversation Enhancement\n')
    lines.insert(import_idx + 1, 'try:\n')
    lines.insert(import_idx + 2, '    from conversation_manager import ConversationStateManager\n')
    lines.insert(import_idx + 3, '    from token_manager import TokenBudgetManager\n')
    lines.insert(import_idx + 4, '    ENHANCEMENT_AVAILABLE = True\n')
    lines.insert(import_idx + 5, 'except ImportError:\n')
    lines.insert(import_idx + 6, '    ENHANCEMENT_AVAILABLE = False\n')
    lines.insert(import_idx + 7, '    print("Enhancement modules not available")\n\n')
    
    print("✅ Imports added")

# Write back
with open('yanay.py', 'w') as f:
    f.writelines(lines)
    
print("✅ File updated")
PYTHON

# Check syntax
echo "4️⃣ Checking syntax..."
python3 -m py_compile yanay.py 2>/dev/null && echo "✅ Syntax valid" || echo "❌ Syntax error"

echo "5️⃣ Restarting Yanay container..."
docker-compose down yanay
sleep 2
docker-compose up -d yanay

echo "6️⃣ Container status:"
docker ps | grep yanay

echo ""
echo "✅ Basic enhancement applied!"
echo "Note: Full conversation features require manual method integration"

ENDSSH

echo ""
echo "📝 Next Steps:"
echo "============="
echo "1. Test basic functionality with @LycurgusBot"
echo "2. Check logs: ssh root@178.156.170.161 'docker logs --tail 50 demestihas-yanay'"
echo "3. For full enhancement, manually add the methods to yanay.py"
