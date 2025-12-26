
# Quick enhancement completion - append to yanay.py
    async def evaluate_response_mode(self, message_text: str, user_id: str) -> str:
        # Check for emotional indicators
        emotional_words = ["frustrated", "tired", "stressed", "excited", "sad", "angry", "happy", "worried", "anxious"]
        if any(word in message_text.lower() for word in emotional_words):
            return "conversational"
        
        # Check for direct task requests  
        task_words = ["add", "create", "schedule", "remind", "set", "book", "plan"]
        if any(message_text.lower().startswith(word) for word in task_words):
            return "task"
            
        # Check for questions
        if message_text.strip().endswith("?") or message_text.lower().startswith(("what", "how", "when", "where", "why")):
            return "conversational"
            
        return "conversational"

    async def opus_conversation(self, message_text: str, user_id: str, context: list) -> str:
        try:
            system_prompt = "You are Yanay, a helpful family AI assistant. Provide warm, conversational responses."
            
            messages = [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": message_text}
            ]
            
            # Use Haiku until API key renewed
            response = await self.anthropic.messages.create(
                model="claude-3-haiku-20240307",
                max_tokens=200,
                messages=messages
            )
            
            return response.content[0].text
            
        except Exception as e:
            logger.error(f"Conversation error: {e}")
            return "I can help with tasks once my conversation system is updated."

