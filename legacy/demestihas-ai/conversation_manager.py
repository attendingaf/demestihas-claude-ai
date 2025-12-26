#!/usr/bin/env python3
"""Conversation State Manager for Yanay.ai - Simplified Implementation"""

import redis
import json
from datetime import datetime
from typing import Dict, List, Optional

class ConversationStateManager:
    """Manages 20-turn conversation window with Redis"""
    
    def __init__(self, redis_host='lyco-redis', redis_port=6379, window_size=20):
        self.redis = redis.Redis(host=redis_host, port=redis_port, decode_responses=True)
        self.window_size = window_size
        
    def get_conversation_context(self, user_id: str, max_turns: int = 10) -> List[Dict]:
        """Get recent conversation turns for context"""
        key = f"conv:{user_id}:turns"
        raw_turns = self.redis.lrange(key, 0, max_turns - 1)
        
        turns = []
        for turn_str in raw_turns:
            try:
                turns.append(json.loads(turn_str))
            except json.JSONDecodeError:
                continue
        
        return turns
    
    def add_turn(self, user_id: str, message: str, response: str, emotion: Optional[str] = None):
        """Add a conversation turn and manage window size"""
        key = f"conv:{user_id}:turns"
        
        turn = {
            "timestamp": datetime.now().isoformat(),
            "message": message,
            "response": response,
            "emotion": emotion or self._detect_emotion(message)
        }
        
        # Add to front of list
        self.redis.lpush(key, json.dumps(turn))
        
        # Trim to window size
        self.redis.ltrim(key, 0, self.window_size - 1)
        
        # Set expiry to 24 hours
        self.redis.expire(key, 86400)
        
        return turn
    
    def _detect_emotion(self, message: str) -> str:
        """Simple emotion detection"""
        message_lower = message.lower()
        
        if any(word in message_lower for word in ["stressed", "worried", "anxious", "overwhelmed"]):
            return "stress"
        elif any(word in message_lower for word in ["happy", "excited", "great", "wonderful"]):
            return "positive"
        elif any(word in message_lower for word in ["sad", "upset", "frustrated", "angry"]):
            return "negative"
        elif "?" in message and any(word in message_lower for word in ["why", "how", "what"]):
            return "curious"
        else:
            return "neutral"
    
    def get_summary(self, user_id: str) -> str:
        """Get a summary of conversation context"""
        turns = self.get_conversation_context(user_id, max_turns=5)
        
        if not turns:
            return "No recent conversation history"
        
        summary_parts = []
        for turn in turns:
            emotion = turn.get('emotion', 'neutral')
            summary_parts.append(f"[{emotion}] User: {turn['message'][:50]}...")
        
        return " | ".join(summary_parts)
