#!/usr/bin/env python3
"""Token Budget Manager for Yanay.ai - $15/day limit"""

import redis
from datetime import datetime
from typing import Dict

class TokenBudgetManager:
    """Manages daily token budget with safeguards"""
    
    def __init__(self, redis_host='lyco-redis', redis_port=6379, daily_limit_usd=15):
        self.redis = redis.Redis(host=redis_host, port=redis_port, decode_responses=True)
        self.daily_limit = daily_limit_usd
        self.opus_cost_per_million = 15  # $15 per 1M tokens
        self.sonnet_cost_per_million = 3  # $3 per 1M tokens (fallback)
        
    def check_budget(self, user_id: str = "family") -> Dict:
        """Check if budget allows Opus usage"""
        key = f"tokens:{datetime.now().date()}:{user_id}"
        
        # Get current usage
        used_usd = float(self.redis.get(key) or 0)
        percentage = (used_usd / self.daily_limit) * 100
        
        # Determine action based on usage
        if percentage >= 100:
            return {
                "allowed": False,
                "model": None,
                "reason": f"Daily limit reached (${used_usd:.2f}/${self.daily_limit})",
                "percentage": percentage
            }
        elif percentage >= 90:
            return {
                "allowed": True,
                "model": "sonnet",  # Fallback to cheaper model
                "warning": f"90% budget used (${used_usd:.2f}/${self.daily_limit})",
                "percentage": percentage
            }
        elif percentage >= 80:
            return {
                "allowed": True,
                "model": "opus",
                "warning": f"80% budget used (${used_usd:.2f}/${self.daily_limit})",
                "percentage": percentage
            }
        else:
            return {
                "allowed": True,
                "model": "opus",
                "percentage": percentage,
                "remaining": self.daily_limit - used_usd
            }
    
    def track_usage(self, tokens_used: int, model: str = "opus", user_id: str = "family"):
        """Track token usage and cost"""
        key = f"tokens:{datetime.now().date()}:{user_id}"
        
        # Calculate cost based on model
        if model == "opus":
            cost = (tokens_used / 1_000_000) * self.opus_cost_per_million
        else:  # sonnet or haiku
            cost = (tokens_used / 1_000_000) * self.sonnet_cost_per_million
        
        # Increment usage
        new_total = self.redis.incrbyfloat(key, cost)
        
        # Set expiry to end of day
        self.redis.expire(key, 86400)
        
        return {
            "tokens_used": tokens_used,
            "cost": cost,
            "daily_total": new_total,
            "percentage": (new_total / self.daily_limit) * 100
        }
    
    def get_usage_stats(self, user_id: str = "family") -> Dict:
        """Get current usage statistics"""
        key = f"tokens:{datetime.now().date()}:{user_id}"
        used_usd = float(self.redis.get(key) or 0)
        
        return {
            "date": str(datetime.now().date()),
            "used_usd": used_usd,
            "limit_usd": self.daily_limit,
            "remaining_usd": self.daily_limit - used_usd,
            "percentage": (used_usd / self.daily_limit) * 100,
            "estimated_messages_remaining": int((self.daily_limit - used_usd) / 0.015)  # ~$0.015 per message
        }
