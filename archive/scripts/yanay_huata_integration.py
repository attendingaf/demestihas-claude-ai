# Yanay-Huata Integration Code
# Code snippets to add to yanay.py for calendar agent integration

# 1. ADD IMPORT AT TOP OF yanay.py
import_code = """
from huata import create_huata_agent
"""

# 2. ADD TO YANAY INITIALIZATION (in __init__ method)
init_code = """
# Initialize Huata Calendar Agent
self.huata = await create_huata_agent(
    anthropic_api_key=os.getenv('ANTHROPIC_API_KEY'),
    redis_host='redis'
)
"""

# 3. ADD CALENDAR INTENT DETECTION (in process_message method)
intent_detection = """
# Check for calendar intents
calendar_keywords = [
    'free', 'available', 'busy', 'schedule', 'calendar', 'meeting',
    'appointment', 'today', 'tomorrow', 'thursday', 'afternoon',
    'morning', 'evening', 'next week', 'time'
]

def contains_calendar_intent(self, message):
    message_lower = message.lower()
    return any(keyword in message_lower for keyword in calendar_keywords)
"""

# 4. ADD CALENDAR ROUTING (in message processing logic)
routing_code = """
# Route calendar queries to Huata
if self.contains_calendar_intent(message):
    try:
        start_time = time.time()
        
        user_context = {
            'user': user_id,
            'username': update.effective_user.first_name,
            'timezone': 'America/New_York'
        }
        
        # Process calendar query with Huata
        response = await self.huata.process_query(message, user_context)
        
        # Calculate response time
        response_time = time.time() - start_time
        user_context['response_time_ms'] = int(response_time * 1000)
        
        await update.message.reply_text(response)
        return
        
    except Exception as e:
        error_msg = "I had trouble with that calendar request. Could you try rephrasing it? 📅"
        await update.message.reply_text(error_msg)
        print(f"Huata error: {e}")
        return
"""

print("Yanay-Huata Integration Code Generated")
print("=" * 40)
print("Integration components prepared:")
print("1. Import statement")
print("2. Agent initialization") 
print("3. Intent detection logic")
print("4. Calendar query routing")
print("\nReady for VPS integration")
