# Update for classify_intent function - add schedule intent
updated_prompt = '''Classify the user's intent from this message.
        
Previous context:
{context_str if context_str else 'No previous context'}

Current message: {message}

Classify as one of:
- create_task: User wants to create a new task
- update_task: User wants to modify an existing task
- query_tasks: User wants to know about their tasks
- schedule: User wants to manage au pair/Viola schedule (days off, coverage, schedule changes)
- general_chat: General conversation

Also identify if the message contains references like 'that', 'it', 'the last one'.

Respond in JSON format:
{{
    "intent": "<classification>",
    "confidence": <0-1>,
    "has_reference": <true/false>,
    "referenced_entity": "<what 'that/it' refers to if applicable>"
}}'''

# Import Nina at the top
import_nina = '''
try:
    from nina import process_schedule_command, check_coverage_gaps
    nina_available = True
except ImportError:
    logger.warning("Nina scheduling agent not found")
    nina_available = False
'''

# Add schedule routing in process_message
schedule_routing = '''
        elif intent['intent'] == 'schedule':
            if nina_available:
                result = await process_schedule_command(user_message, user_name)
                response = result.get('message', '📅 Processing schedule request...')
                
                # Create task if coverage needed
                if result.get('create_task'):
                    task_result = await self.route_to_lyco('create_task', {
                        'text': result.get('task_title', 'Coverage needed'),
                        'user_name': user_name
                    })
            else:
                response = "❌ Schedule management not available"
'''
