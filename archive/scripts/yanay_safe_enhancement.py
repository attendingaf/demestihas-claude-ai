#!/usr/bin/env python3
"""
Minimal safe enhancement for yanay.py
This adds just the essential conversation tracking without breaking syntax
"""

# This code can be added to the END of yanay.py as a standalone enhancement

# Enhancement check - add this at the very end of yanay.py
def apply_conversation_enhancement():
    """
    Safe enhancement that can be added to end of yanay.py
    Call this from the main bot initialization
    """
    try:
        from conversation_manager import ConversationStateManager
        from token_manager import TokenBudgetManager
        
        # Create global instances
        global conversation_manager, token_manager
        conversation_manager = ConversationStateManager()
        token_manager = TokenBudgetManager()
        
        print("✅ Conversation enhancement loaded")
        return True
    except Exception as e:
        print(f"⚠️ Enhancement not available: {e}")
        return False

# Message wrapper - add this function
def enhance_message_processing(original_function):
    """
    Decorator to add conversation tracking to any message processing function
    """
    def wrapper(message_text, user_id, *args, **kwargs):
        # Run original processing
        response = original_function(message_text, user_id, *args, **kwargs)
        
        # Add conversation tracking if available
        try:
            if 'conversation_manager' in globals():
                conversation_manager.add_turn(
                    str(user_id), 
                    message_text, 
                    response if response else "Processing..."
                )
                print(f"📝 Conversation tracked for user {user_id}")
        except Exception as e:
            print(f"Tracking error: {e}")
        
        return response
    
    return wrapper

# Initialize enhancement when module loads
if __name__ != "__main__":  # Only when imported
    apply_conversation_enhancement()
