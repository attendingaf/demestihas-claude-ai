#!/bin/bash
# Automated Yanay.ai Enhancement Integration using sed
# No manual editing required!

echo "🔧 Yanay.ai Automated Integration Script"
echo "========================================"

# Create the integration commands
cat << 'EOF' > /tmp/yanay_integration.sh
#!/bin/bash
cd /root/demestihas-ai

# Backup original
echo "📦 Creating backup..."
cp yanay.py yanay.py.backup.$(date +%Y%m%d_%H%M%S)

# Step 1: Add new imports after existing imports
echo "📝 Adding new imports..."
# Find the last import line and add our imports after it
sed -i '/^import\|^from/h;${x;s/$/\n# Conversation Enhancement Imports\nfrom conversation_manager import ConversationStateManager\nfrom token_manager import TokenBudgetManager\nfrom anthropic import Anthropic/;x;}' yanay.py

# Step 2: Add initialization in __init__ method
echo "🔧 Adding managers to __init__..."
# Find __init__ method and add our initialization
sed -i '/__init__.*self/,/^[[:space:]]*def /{
    /self\./h
    /self\./!d
    x
    /self\./{
        a\        # Conversation Enhancement Components\
        self.conversation_manager = ConversationStateManager()\
        self.token_manager = TokenBudgetManager()\
        try:\
            self.opus_client = Anthropic(api_key=os.getenv("ANTHROPIC_OPUS_KEY", os.getenv("ANTHROPIC_API_KEY")))\
        except:\
            self.opus_client = None\
            print("Warning: Opus client not initialized")
    }
}' yanay.py

# Step 3: Add the intelligent routing method
echo "📊 Adding intelligent routing method..."
cat << 'METHOD1' >> yanay_methods.tmp

    async def evaluate_response_mode(self, message: str, user_id: str, username: str = None):
        """Intelligent override - evaluates best response approach"""
        context = self.conversation_manager.get_summary(user_id) if hasattr(self, 'conversation_manager') else ""
        
        # Simple keyword-based routing for now
        message_lower = message.lower()
        
        # Check for emotional content
        emotional_words = ['stress', 'worried', 'anxious', 'happy', 'sad', 'frustrated']
        if any(word in message_lower for word in emotional_words):
            return {"mode": "conversation", "reason": "emotional_content"}
        
        # Check for educational queries
        if message_lower.startswith(('why', 'how', 'what is', 'explain')):
            return {"mode": "conversation", "reason": "educational"}
        
        # Check for direct calendar tasks
        calendar_words = ['appointment', 'meeting', 'schedule', 'calendar']
        if any(word in message_lower for word in calendar_words):
            return {"mode": "delegation", "agent": "huata", "reason": "calendar_task"}
        
        # Check for task management
        task_words = ['task', 'todo', 'project', 'remind']
        if any(word in message_lower for word in task_words):
            return {"mode": "delegation", "agent": "lyco", "reason": "task_management"}
        
        # Default to conversation for ambiguous
        return {"mode": "conversation", "reason": "default"}
METHOD1

# Step 4: Add the Opus conversation method
cat << 'METHOD2' >> yanay_methods.tmp

    async def opus_conversation(self, message: str, user_id: str, username: str = None):
        """Handle conversational responses with Opus"""
        if not hasattr(self, 'opus_client') or self.opus_client is None:
            return "I'm having trouble with advanced conversations. Let me help you simply."
        
        # Check token budget
        budget_status = self.token_manager.check_budget(user_id)
        
        if not budget_status["allowed"]:
            return f"⚠️ {budget_status['reason']}. Some features may be limited until tomorrow."
        
        # Get conversation history
        conversation_history = self.conversation_manager.get_conversation_context(user_id, max_turns=5)
        
        # Build simple prompt
        history_text = ""
        for turn in conversation_history[-3:]:
            history_text += f"User: {turn.get('message', '')[:100]}\n"
            history_text += f"Assistant: {turn.get('response', '')[:100]}\n"
        
        prompt = f"""You are Yanay, a warm and helpful AI assistant for the Demestihas family.

Recent conversation:
{history_text}

Current message: {message}

Respond naturally and helpfully. Be concise but warm."""
        
        try:
            model = "claude-3-opus-20240229" if budget_status.get("model") == "opus" else "claude-3-sonnet-20240229"
            
            response = self.opus_client.messages.create(
                model=model,
                max_tokens=500,
                messages=[{"role": "user", "content": prompt}]
            )
            
            response_text = response.content[0].text
            
            # Save conversation turn
            self.conversation_manager.add_turn(user_id, message, response_text)
            
            return response_text
            
        except Exception as e:
            print(f"Opus conversation error: {e}")
            return "I understand you need help. Let me process that for you."
METHOD2

# Find the last method in the class and append our new methods
echo "📎 Appending new methods to class..."
# This finds the class definition and appends methods before the next class or end of file
awk '/^class YanayOrchestrator/,/^class |^$/{p=1} p' yanay.py > yanay_temp.py
cat yanay_methods.tmp >> yanay_temp.py
mv yanay_temp.py yanay.py
rm yanay_methods.tmp

# Step 5: Modify the main message processing to use intelligent routing
echo "🔄 Modifying message processing..."
# Find process_message or similar and add routing
sed -i '/async def process.*message/,/^[[:space:]]*async def \|^class /{
    /async def process/a\        # Intelligent routing decision\
        try:\
            decision = await self.evaluate_response_mode(message, user_id, username)\
            \
            if decision.get("mode") == "conversation":\
                response = await self.opus_conversation(message, user_id, username)\
                return response\
        except Exception as e:\
            print(f"Routing error: {e}, falling back to normal processing")
}' yanay.py

echo "✅ Integration complete!"
echo "📋 Verifying changes..."

# Check if imports were added
if grep -q "conversation_manager import" yanay.py; then
    echo "✅ Imports added successfully"
else
    echo "⚠️ Imports may need manual verification"
fi

# Check if methods were added
if grep -q "evaluate_response_mode" yanay.py; then
    echo "✅ Methods added successfully"
else
    echo "⚠️ Methods may need manual verification"
fi

echo ""
echo "🎯 Next steps:"
echo "1. Review yanay.py for any syntax issues"
echo "2. Restart container: docker-compose restart yanay"
echo "3. Monitor logs: docker logs -f demestihas-yanay"
EOF

# Make it executable
chmod +x /tmp/yanay_integration.sh

echo "📤 Uploading integration script to VPS..."
scp /tmp/yanay_integration.sh root@178.156.170.161:/root/demestihas-ai/

echo "🚀 Ready to execute on VPS!"
echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "EXECUTE THESE COMMANDS:"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""
echo "1. SSH to VPS:"
echo "   ssh root@178.156.170.161"
echo ""
echo "2. Run integration:"
echo "   cd /root/demestihas-ai"
echo "   bash yanay_integration.sh"
echo ""
echo "3. Quick syntax check:"
echo "   python3 -m py_compile yanay.py"
echo ""
echo "4. If syntax OK, restart:"
echo "   docker-compose restart yanay"
echo ""
echo "5. Monitor logs:"
echo "   docker logs -f demestihas-yanay"
echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
