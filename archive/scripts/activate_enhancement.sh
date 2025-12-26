#!/bin/bash
# activate_yanay_enhancement.sh - Quick fix to enable conversational mode

echo "🔧 Activating Yanay Conversational Enhancement..."

ssh root@178.156.170.161 << 'ENDSSH'
cd /root/demestihas-ai

# Create activation script
cat > activate_enhancement.py << 'EOFPY'
#!/usr/bin/env python3
import re

print("📖 Reading yanay.py...")
with open('yanay.py', 'r') as f:
    content = f.read()

# Check if already active
if 'evaluate_response_mode(message_text)' in content:
    print("✅ Enhancement already active!")
    exit(0)

print("🔧 Patching handle_message method...")

# Find the handle_message method and inject enhancement
old_pattern = '''        # Classify intent
        intent = await self.classify_intent(message_text)
        logger.info(f"Intent classified: {intent}")'''

new_pattern = '''        # Check conversational mode first
        try:
            mode = self.evaluate_response_mode(message_text)
            logger.info(f"Response mode: {mode}")
            
            if mode == 'conversational':
                logger.info("Using Opus for conversational response")
                response = await self.opus_conversation(message_text, user_id)
                await self.send_message(chat_id, response)
                return
        except Exception as e:
            logger.error(f"Enhancement error: {e}, using normal flow")
        
        # Classify intent (fallback)
        intent = await self.classify_intent(message_text)
        logger.info(f"Intent classified: {intent}")'''

if old_pattern in content:
    content = content.replace(old_pattern, new_pattern)
    with open('yanay.py', 'w') as f:
        f.write(content)
    print("✅ Enhancement activated successfully!")
else:
    print("⚠️ Pattern not found - manual update needed")
    print("Looking for: 'Classify intent' section in handle_message")
EOFPY

# Run the activation
python3 activate_enhancement.py

# Restart container
echo "🔄 Restarting Yanay container..."
docker restart demestihas-yanay

# Wait for startup
sleep 5

# Verify activation
echo "📋 Verifying enhancement activation..."
docker logs --tail 30 demestihas-yanay | grep -E "(Response mode|evaluate|opus|conversational)" || echo "No enhancement logs yet - send a test message"

echo "✅ Enhancement activation complete!"
echo ""
echo "🧪 Test with these messages:"
echo "1. 'I am feeling stressed' - should trigger conversational mode"
echo "2. 'Add task: review docs' - should trigger task mode"
echo "3. 'Why is the sky blue?' - should trigger educational conversation"

ENDSSH
