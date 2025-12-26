#!/usr/bin/env python3
"""
Huata Integration Patch for Yanay
Adds calendar agent integration to existing Yanay orchestrator
"""

import re
import sys

def apply_huata_integration_patch(yanay_file_path):
    """Apply Huata integration patch to yanay.py"""
    
    print("🔧 Applying Huata integration patch...")
    
    # Read current yanay.py
    with open(yanay_file_path, 'r') as f:
        content = f.read()
    
    # 1. Add Huata import after other imports
    import_pattern = r'(import os\s*\n|from anthropic import.*\n)'
    huata_import = '\nfrom huata import create_huata_agent\n'
    
    if 'from huata import create_huata_agent' not in content:
        content = re.sub(import_pattern, r'\1' + huata_import, content, count=1)
        print("✅ Added Huata import")
    else:
        print("✅ Huata import already present")
    
    # 2. Add Huata initialization to __init__ method
    init_pattern = r'(\s+)self\.redis = redis\.Redis\([^)]+\)'
    huata_init = r'\1self.redis = redis.Redis(host=redis_host, port=redis_port, decode_responses=True)\n\1\n\1# Initialize Huata Calendar Agent\n\1self.huata = None  # Will be initialized asynchronously'
    
    if 'self.huata = None' not in content:
        content = re.sub(init_pattern, huata_init, content)
        print("✅ Added Huata initialization placeholder")
    else:
        print("✅ Huata initialization already present")
    
    # 3. Add calendar intent detection method
    intent_method = '''
    def contains_calendar_intent(self, message):
        """Check if message contains calendar-related intent"""
        calendar_keywords = [
            'free', 'available', 'busy', 'schedule', 'calendar', 'meeting',
            'appointment', 'today', 'tomorrow', 'thursday', 'afternoon',
            'morning', 'evening', 'next week', 'time', 'when', 'what time',
            # Event/meeting references
            'event', 'events', 'meetings', 'appointments'
        ]
        message_lower = message.lower()
        return any(keyword in message_lower for keyword in calendar_keywords)
    '''
    
    if 'contains_calendar_intent' not in content:
        # Find a good place to insert the method (before process_message)
        method_pattern = r'(\s+async def process_message\(self[^:]+:\s*\n)'
        content = re.sub(method_pattern, intent_method + r'\1', content)
        print("✅ Added calendar intent detection method")
    else:
        print("✅ Calendar intent detection already present")
    
    # 4. Add Huata async initialization
    async_init = '''
        # Initialize Huata Calendar Agent asynchronously
        if self.huata is None:
            try:
                self.huata = await create_huata_agent(
                    anthropic_api_key=os.getenv('ANTHROPIC_API_KEY'),
                    redis_host='redis'
                )
                print("✅ Huata Calendar Agent initialized")
            except Exception as e:
                print(f"⚠️ Huata initialization warning: {e}")
    '''
    
    if 'create_huata_agent' not in content or 'Initialize Huata Calendar Agent asynchronously' not in content:
        # Add to beginning of process_message method
        process_pattern = r'(\s+async def process_message\(self[^:]+:\s*\n)(\s+)(.*)'
        content = re.sub(process_pattern, r'\1\2' + async_init.strip() + '\n\n\2\3', content, count=1)
        print("✅ Added async Huata initialization")
    else:
        print("✅ Async Huata initialization already present")
    
    # 5. Add calendar routing logic (insert before existing routing logic)
    calendar_routing = '''        # Handle calendar queries with Huata
        if self.contains_calendar_intent(message) and self.huata:
            try:
                import time
                start_time = time.time()
                
                user_context = {
                    'user': 'mene',  # TODO: Extract from update
                    'username': update.effective_user.first_name if update.effective_user else 'User',
                    'timezone': 'America/New_York'
                }
                
                # Process calendar query with Huata
                response = await self.huata.process_query(message, user_context)
                
                # Log response time
                response_time = time.time() - start_time
                print(f"🗓️ Huata response time: {response_time:.2f}s")
                
                await update.message.reply_text(response)
                return
                
            except Exception as e:
                error_msg = "I had trouble with that calendar request. Could you try rephrasing it? 📅"
                await update.message.reply_text(error_msg)
                print(f"❌ Huata error: {e}")
                return

'''
    
    if 'Handle calendar queries with Huata' not in content:
        # Find where to insert routing logic - look for task processing
        routing_pattern = r'(\s+# Process the message.*\n|\s+# Extract task.*\n)'
        content = re.sub(routing_pattern, calendar_routing + r'\1', content, count=1)
        print("✅ Added calendar routing logic")
    else:
        print("✅ Calendar routing already present")
    
    # Write updated content back
    with open(yanay_file_path, 'w') as f:
        f.write(content)
    
    print("🎉 Huata integration patch applied successfully!")
    return True

if __name__ == "__main__":
    yanay_path = sys.argv[1] if len(sys.argv) > 1 else "yanay.py"
    apply_huata_integration_patch(yanay_path)
