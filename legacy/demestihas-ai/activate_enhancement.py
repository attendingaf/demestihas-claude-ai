#!/usr/bin/env python3
import re

print('Reading yanay.py...')
with open('yanay.py', 'r') as f:
    content = f.read()

if 'evaluate_response_mode(message_text)' in content:
    print('Enhancement already active!')
    exit(0)

print('Patching handle_message...')
old = '''        # Classify intent
        intent = await self.classify_intent(message_text)
        logger.info(f"Intent classified: {intent}")'''

new = '''        # Check conversational mode first
        try:
            mode = self.evaluate_response_mode(message_text)
            logger.info(f"Response mode: {mode}")
            
            if mode == 'conversational':
                response = await self.opus_conversation(message_text, user_id)
                await self.send_message(chat_id, response)
                return
        except Exception as e:
            logger.error(f"Enhancement error: {e}")
        
        # Classify intent (fallback)
        intent = await self.classify_intent(message_text)
        logger.info(f"Intent classified: {intent}")'''

if old in content:
    content = content.replace(old, new)
    with open('yanay.py', 'w') as f:
        f.write(content)
    print('Enhancement activated!')
else:
    print('Pattern not found, checking alternative...')
    # Try simpler replacement
    if 'await self.classify_intent(message_text)' in content:
        print('Found classify_intent, applying patch...')
