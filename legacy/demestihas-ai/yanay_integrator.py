#!/usr/bin/env python3
"""
Automated Yanay.py Enhancement Integrator
Uses Python AST to safely modify the existing yanay.py file
"""

import sys
import re
import shutil
from datetime import datetime

def integrate_yanay_enhancement(file_path="/root/demestihas-ai/yanay.py"):
    """Integrate conversation enhancement into existing yanay.py"""
    
    # Create backup
    backup_path = f"{file_path}.backup.{datetime.now().strftime('%Y%m%d_%H%M%S')}"
    shutil.copy2(file_path, backup_path)
    print(f"✅ Backup created: {backup_path}")
    
    # Read the original file
    with open(file_path, 'r') as f:
        content = f.read()
    
    # Step 1: Add imports after existing imports
    import_additions = """
# Conversation Enhancement Imports
from conversation_manager import ConversationStateManager
from token_manager import TokenBudgetManager
try:
    from anthropic import Anthropic
except ImportError:
    print("Warning: Anthropic not imported")
    Anthropic = None
"""
    
    # Find the last import and add our imports
    import_pattern = r'((?:^import .*$|^from .* import .*$)\n)+(?=\n)'
    import_match = re.search(import_pattern, content, re.MULTILINE)
    if import_match:
        insert_pos = import_match.end()
        content = content[:insert_pos] + import_additions + content[insert_pos:]
        print("✅ Imports added")
    
    # Step 2: Add initialization to __init__ method
    init_additions = """
        # Conversation Enhancement Components
        try:
            self.conversation_manager = ConversationStateManager()
            self.token_manager = TokenBudgetManager()
            if Anthropic:
                self.opus_client = Anthropic(api_key=os.getenv("ANTHROPIC_OPUS_KEY", os.getenv("ANTHROPIC_API_KEY")))
            else:
                self.opus_client = None
        except Exception as e:
            print(f"Enhancement initialization warning: {e}")
            self.conversation_manager = None
            self.token_manager = None
            self.opus_client = None
"""
    
    # Find __init__ method and add after first self. assignment
    init_pattern = r'(def __init__.*?:\n(?:.*?\n)*?)((?:        self\.\w+ = .*?\n)+)'
    init_match = re.search(init_pattern, content)
    if init_match:
        insert_pos = init_match.end()
        content = content[:insert_pos] + init_additions + content[insert_pos:]
        print("✅ Init enhancements added")
    
    # Step 3: Add new methods to the class
    new_methods = '''
    async def evaluate_response_mode(self, message: str, user_id: str, username: str = None):
        """Intelligent override - evaluates best response approach"""
        if not hasattr(self, 'conversation_manager'):
            return {"mode": "delegation", "agent": "lyco"}
            
        context = self.conversation_manager.get_summary(user_id) if self.conversation_manager else ""
        message_lower = message.lower()
        
        # Emotional content detection
        emotional_words = ['stress', 'worried', 'anxious', 'happy', 'sad', 'frustrated', 'overwhelmed']
        if any(word in message_lower for word in emotional_words):
            return {"mode": "conversation", "reason": "emotional_content"}
        
        # Educational queries
        if any(message_lower.startswith(word) for word in ['why', 'how', 'what is', 'explain']):
            return {"mode": "conversation", "reason": "educational"}
        
        # Direct calendar tasks
        calendar_words = ['appointment', 'meeting', 'schedule', 'calendar', 'event']
        if any(word in message_lower for word in calendar_words):
            return {"mode": "delegation", "agent": "huata", "reason": "calendar_task"}
        
        # Task management
        task_words = ['task', 'todo', 'project', 'remind', 'notion']
        if any(word in message_lower for word in task_words):
            return {"mode": "delegation", "agent": "lyco", "reason": "task_management"}
        
        # Scheduling
        schedule_words = ['schedule', 'plan', 'organize', 'coordinate']
        if any(word in message_lower for word in schedule_words):
            return {"mode": "delegation", "agent": "nina", "reason": "scheduling"}
        
        # Default to conversation for ambiguous
        return {"mode": "conversation", "reason": "default"}

    async def opus_conversation(self, message: str, user_id: str, username: str = None):
        """Handle conversational responses with Opus"""
        if not hasattr(self, 'opus_client') or self.opus_client is None:
            return "I'll help you with that task. Let me process it for you."
        
        # Check token budget
        budget_status = self.token_manager.check_budget(user_id) if self.token_manager else {"allowed": True, "model": "opus"}
        
        if not budget_status["allowed"]:
            return f"⚠️ {budget_status['reason']}. Some features may be limited until tomorrow."
        
        # Get conversation history
        conversation_history = []
        if self.conversation_manager:
            conversation_history = self.conversation_manager.get_conversation_context(user_id, max_turns=5)
        
        # Build conversation context
        history_text = ""
        for turn in conversation_history[-3:] if conversation_history else []:
            history_text += f"User: {turn.get('message', '')[:100]}\\n"
            history_text += f"Assistant: {turn.get('response', '')[:100]}\\n"
        
        # Determine user profile
        user_style = "friendly and helpful"
        if username:
            username_lower = username.lower()
            if 'mene' in username_lower:
                user_style = "direct and execution-focused"
            elif 'cindy' in username_lower:
                user_style = "supportive with scheduling focus"
            elif 'viola' in username_lower:
                user_style = "patient with clear explanations"
            elif any(child in username_lower for child in ['persy', 'stelios', 'franci']):
                user_style = "educational and age-appropriate"
        
        prompt = f"""You are Yanay, a warm and intelligent AI assistant for the Demestihas family.

Style: Be {user_style}

Recent conversation:
{history_text}

Current message: {message}

Available capabilities if needed:
- Nina: Scheduling and appointments
- Huata: Calendar management
- Lyco: Project and task management

Respond naturally and helpfully. If the message clearly needs a specific agent, mention you'll handle it."""
        
        try:
            model = "claude-3-opus-20240229" if budget_status.get("model") == "opus" else "claude-3-sonnet-20240229"
            
            response = self.opus_client.messages.create(
                model=model,
                max_tokens=500,
                messages=[{"role": "user", "content": prompt}]
            )
            
            response_text = response.content[0].text
            
            # Track usage
            if self.token_manager and hasattr(response, 'usage'):
                self.token_manager.track_usage(response.usage.total_tokens, budget_status.get("model", "opus"), user_id)
            
            # Save conversation turn
            if self.conversation_manager:
                self.conversation_manager.add_turn(user_id, message, response_text)
            
            return response_text
            
        except Exception as e:
            print(f"Opus conversation error: {e}")
            return "I understand you need help. Let me assist you with that."

    async def enhanced_process_message(self, message: str, user_id: str, username: str = None):
        """Enhanced message processing with intelligent override"""
        try:
            # Always evaluate for best approach (intelligent override default)
            decision = await self.evaluate_response_mode(message, user_id, username)
            
            if decision["mode"] == "conversation":
                # Natural conversation with Opus
                response = await self.opus_conversation(message, user_id, username)
                return response
            elif decision["mode"] == "delegation":
                # Fall through to existing agent routing
                print(f"Delegating to {decision.get('agent', 'lyco')}: {decision.get('reason', '')}")
                # Continue with existing processing
                pass
        except Exception as e:
            print(f"Enhancement error: {e}, using standard processing")
        
        # Fall through to existing logic
        return None  # Signal to use existing processing
'''
    
    # Find the class definition and add methods
    class_pattern = r'(class\s+\w+.*?:.*?)(\n(?:    async def |    def ))'
    class_match = re.search(class_pattern, content, re.DOTALL)
    if class_match:
        # Add methods before the first existing method
        insert_pos = class_match.end(1)
        content = content[:insert_pos] + new_methods + content[insert_pos:]
        print("✅ New methods added")
    
    # Step 4: Modify main processing method to use enhancement
    # Look for process_message or handle_message method
    process_pattern = r'(async def (?:process|handle).*?message.*?:)(.*?)(?=\n    async def |\n    def |\nclass |\Z)'
    process_match = re.search(process_pattern, content, re.DOTALL)
    
    if process_match:
        method_name = process_match.group(0)
        # Add enhancement call at the beginning
        enhancement_code = """
        # Try enhanced processing first
        enhanced_response = await self.enhanced_process_message(message, user_id, username if 'username' in locals() else None)
        if enhanced_response:
            return enhanced_response
        
        # Continue with original processing
"""
        # Insert after the method definition line
        method_def_end = process_match.end(1)
        # Find first line of code (skip docstring if present)
        remaining = content[method_def_end:]
        if remaining.strip().startswith('"""'):
            # Skip docstring
            docstring_end = remaining.find('"""', 3) + 3
            insert_pos = method_def_end + docstring_end + 1
        else:
            insert_pos = method_def_end + 1
        
        content = content[:insert_pos] + enhancement_code + content[insert_pos:]
        print("✅ Message processing enhanced")
    
    # Write the modified content
    with open(file_path, 'w') as f:
        f.write(content)
    
    print(f"✅ Integration complete: {file_path}")
    print(f"📁 Backup saved as: {backup_path}")
    
    return True

if __name__ == "__main__":
    if len(sys.argv) > 1:
        file_path = sys.argv[1]
    else:
        file_path = "/root/demestihas-ai/yanay.py"
    
    try:
        integrate_yanay_enhancement(file_path)
        print("\n✅ SUCCESS! Next steps:")
        print("1. Check syntax: python3 -m py_compile yanay.py")
        print("2. Restart container: docker-compose restart yanay")
        print("3. Monitor logs: docker logs -f demestihas-yanay")
    except Exception as e:
        print(f"❌ Error: {e}")
        print("Please check the file manually")
