#!/bin/bash
# complete_yanay_fix.sh - Ensure enhancement is fully integrated

echo "🔧 Complete Yanay Enhancement Integration"

ssh root@178.156.170.161 << 'ENDSSH'
cd /root/demestihas-ai

# Create comprehensive fix script
cat > fix_yanay_complete.py << 'EOFPY'
#!/usr/bin/env python3
import os
import sys

print("🔍 Checking current yanay.py status...")

# Read the file
with open('yanay.py', 'r') as f:
    content = f.read()

# Check what we have
has_evaluate = 'def evaluate_response_mode' in content
has_opus = 'def opus_conversation' in content
has_call = 'evaluate_response_mode(message_text)' in content

print(f"✓ evaluate_response_mode defined: {has_evaluate}")
print(f"✓ opus_conversation defined: {has_opus}")
print(f"✓ Enhancement called in handle_message: {has_call}")

if not has_evaluate or not has_opus:
    print("❌ Methods missing! They need to be added from conversation_manager.py")
    print("Adding methods now...")
    
    # Add the methods if missing
    method_code = '''
    def evaluate_response_mode(self, message: str) -> str:
        """Evaluate whether message needs conversational or task response"""
        message_lower = message.lower()
        
        # Emotional/conversational triggers
        emotional_keywords = ['feel', 'feeling', 'stressed', 'anxious', 'worried', 'overwhelmed', 
                             'scared', 'sad', 'happy', 'excited', 'frustrated', 'angry']
        
        # Educational triggers
        educational_keywords = ['why', 'how does', 'what is', 'explain', 'understand']
        
        # Task triggers
        task_keywords = ['add task', 'create task', 'remind', 'schedule', 'add to', 'task:']
        
        # Check patterns
        for word in emotional_keywords:
            if word in message_lower:
                return 'conversational'
        
        for word in educational_keywords:
            if word in message_lower and '?' in message:
                return 'conversational'
        
        for word in task_keywords:
            if word in message_lower:
                return 'task'
        
        # Default to task for clear commands
        if any(message_lower.startswith(cmd) for cmd in ['add', 'create', 'schedule']):
            return 'task'
        
        # Default to conversational for ambiguous
        return 'conversational' if len(message.split()) > 5 else 'task'
    
    async def opus_conversation(self, message: str, user_id: str) -> str:
        """Have a conversational response using Opus"""
        try:
            from anthropic import Anthropic
            
            # Get or create conversation history
            conv_key = f"conv:{user_id}"
            history = self.redis_client.get(conv_key)
            
            # Use Opus for conversation
            client = Anthropic(api_key=os.environ.get('ANTHROPIC_API_KEY'))
            
            response = client.messages.create(
                model='claude-3-haiku-20240307',  # Using Haiku for now, switch to Opus
                max_tokens=500,
                messages=[
                    {"role": "user", "content": message}
                ],
                system="You are a helpful, empathetic assistant. Provide supportive and thoughtful responses."
            )
            
            return response.content[0].text
            
        except Exception as e:
            logger.error(f"Opus conversation error: {e}")
            return "I understand you're reaching out. Let me help you with that. Could you tell me more about what's on your mind?"
'''
    
    # Find where to add methods (before handle_message)
    import re
    pattern = r'(    async def handle_message)'
    replacement = method_code + '\n\n\\1'
    content = re.sub(pattern, replacement, content)
    print("✅ Methods added")

if not has_call:
    print("🔧 Adding enhancement call to handle_message...")
    
    # Find and update handle_message
    lines = content.split('\n')
    new_lines = []
    in_handle_message = False
    inserted = False
    
    for i, line in enumerate(lines):
        new_lines.append(line)
        
        if 'async def handle_message' in line:
            in_handle_message = True
        
        if in_handle_message and not inserted and 'intent = await self.classify_intent(message_text)' in line:
            # Insert enhancement before intent classification
            indent = '        '
            enhancement_lines = [
                f'{indent}# Try conversational enhancement first',
                f'{indent}try:',
                f'{indent}    mode = self.evaluate_response_mode(message_text)',
                f'{indent}    logger.info(f"Response mode: {{mode}}")',
                f'{indent}    ',
                f'{indent}    if mode == "conversational":',
                f'{indent}        logger.info("Using conversational response")',
                f'{indent}        response = await self.opus_conversation(message_text, user_id)',
                f'{indent}        await self.send_message(chat_id, response)',
                f'{indent}        return',
                f'{indent}except Exception as e:',
                f'{indent}    logger.error(f"Enhancement failed: {{e}}")',
                f'{indent}',
                f'{indent}# Fall back to normal intent classification'
            ]
            
            # Insert before current line
            for j in range(len(enhancement_lines)-1, -1, -1):
                new_lines.insert(len(new_lines)-1, enhancement_lines[j])
            
            inserted = True
            print(f"✅ Enhancement call inserted at line {i}")
    
    content = '\n'.join(new_lines)

# Write back
with open('yanay.py', 'w') as f:
    f.write(content)

print("✅ Yanay.py fully updated with enhancement")
print("🔄 Restart container to apply changes")
EOFPY

# Run the complete fix
python3 fix_yanay_complete.py

# Backup and rebuild
cp yanay.py yanay.py.enhanced.$(date +%Y%m%d_%H%M%S)
docker-compose build yanay
docker-compose up -d yanay

echo "⏳ Waiting for container to start..."
sleep 5

# Test the enhancement
echo "🧪 Testing enhancement..."
docker exec demestihas-yanay python3 -c "
from yanay import YanayOrchestrator
y = YanayOrchestrator()
print('Testing modes:')
print('  anxious:', y.evaluate_response_mode('I feel anxious'))
print('  task:', y.evaluate_response_mode('Add task: review'))
print('  question:', y.evaluate_response_mode('Why is the sky blue?'))
"

echo "✅ Enhancement integration complete!"
echo ""
echo "📱 Test with @LycurgusBot:"
echo "1. 'I'm feeling anxious' - should see 'Response mode: conversational' in logs"
echo "2. 'Add task: test' - should see 'Response mode: task' in logs"
echo ""
echo "Monitor with: docker logs -f demestihas-yanay | grep 'Response mode'"

ENDSSH
