"""
Intelligent model router for cost optimization.
Decides between Claude Haiku (fast/cheap) and Sonnet (powerful/expensive).
"""

import logging
import json
from typing import Dict, Any, Literal, Optional
from datetime import datetime, timedelta
import redis
from dataclasses import dataclass, asdict
from enum import Enum

logger = logging.getLogger(__name__)

class TaskComplexity(Enum):
    SIMPLE = "simple"       # Use Haiku
    MODERATE = "moderate"   # Use Haiku with enhanced prompt
    COMPLEX = "complex"     # Use Sonnet
    CRITICAL = "critical"   # Always use Sonnet

@dataclass
class ModelUsageMetrics:
    """Track model usage for cost optimization"""
    timestamp: datetime
    model: str
    complexity: str
    tokens_in: int
    tokens_out: int
    cost_usd: float
    response_time_ms: float
    task_type: str
    success: bool

class ModelRouter:
    """
    Intelligently routes requests to appropriate Claude model based on:
    - Task complexity
    - User preferences
    - Cost thresholds
    - Historical performance
    """
    
    # Pricing per million tokens
    PRICING = {
        "haiku": {"input": 0.25, "output": 1.25},
        "sonnet": {"input": 3.00, "output": 15.00}
    }
    
    # Complexity indicators
    COMPLEXITY_INDICATORS = {
        "simple": [
            "buy", "remind", "add", "schedule", "call", "email",
            "pick up", "drop off", "get", "find"
        ],
        "complex": [
            "plan", "analyze", "coordinate", "organize", "research",
            "evaluate", "decide", "compare", "strategy", "multiple"
        ],
        "family": [
            "viola", "cindy", "persy", "stelios", "franci",
            "family", "kids", "everyone", "coordinate"
        ],
        "urgent": [
            "urgent", "emergency", "asap", "now", "immediately",
            "critical", "deadline", "today"
        ]
    }
    
    def __init__(self, redis_client: redis.Redis, cost_threshold_daily: float = 10.0):
        self.redis = redis_client
        self.cost_threshold_daily = cost_threshold_daily
        self.usage_key = "lyco:model_usage"
        self.config_key = "lyco:model_config"
        
        # Load or set default configuration
        self._load_config()
    
    def _load_config(self):
        """Load model routing configuration from Redis"""
        config = self.redis.get(self.config_key)
        if config:
            self.config = json.loads(config)
        else:
            # Default configuration
            self.config = {
                "sonnet_threshold": 0.3,  # Use Sonnet 30% of time max
                "force_haiku_under_cost": 8.0,  # Force Haiku if daily cost > $8
                "complexity_weights": {
                    "simple": 0.0,
                    "complex": 0.6,
                    "family": 0.3,
                    "urgent": 0.4
                },
                "test_mode": False
            }
            self.redis.set(self.config_key, json.dumps(self.config))
    
    def analyze_complexity(self, message: str, context: Dict[str, Any]) -> TaskComplexity:
        """
        Analyze message complexity to determine appropriate model.
        
        Returns TaskComplexity enum indicating routing decision.
        """
        message_lower = message.lower()
        complexity_score = 0.0
        
        # Check for complexity indicators
        indicators_found = {
            "simple": 0,
            "complex": 0,
            "family": 0,
            "urgent": 0
        }
        
        for category, keywords in self.COMPLEXITY_INDICATORS.items():
            for keyword in keywords:
                if keyword in message_lower:
                    indicators_found[category] += 1
        
        # Calculate weighted complexity score
        weights = self.config["complexity_weights"]
        for category, count in indicators_found.items():
            if count > 0:
                complexity_score += weights.get(category, 0.0) * min(count, 3)
        
        # Context-based adjustments
        if context.get("multiple_tasks"):
            complexity_score += 0.3
        
        if context.get("requires_search"):
            complexity_score += 0.2
        
        if context.get("cross_family_coordination"):
            complexity_score += 0.4
        
        # Check for specific patterns requiring Sonnet
        if self._requires_sonnet(message, context):
            return TaskComplexity.CRITICAL
        
        # Determine complexity level
        if complexity_score >= 0.8:
            return TaskComplexity.COMPLEX
        elif complexity_score >= 0.4:
            return TaskComplexity.MODERATE
        else:
            return TaskComplexity.SIMPLE
    
    def _requires_sonnet(self, message: str, context: Dict[str, Any]) -> bool:
        """Check if message absolutely requires Sonnet"""
        # Family scheduling across multiple members
        if "everyone" in message.lower() and any(
            word in message.lower() for word in ["schedule", "coordinate", "plan"]
        ):
            return True
        
        # Complex medical/work decisions
        if context.get("user_role") == "physician" and any(
            word in message.lower() for word in ["patient", "diagnosis", "treatment"]
        ):
            return True
        
        # Financial planning
        if any(word in message.lower() for word in ["budget", "investment", "financial"]):
            return True
        
        return False
    
    def get_daily_cost(self) -> float:
        """Calculate today's total model costs"""
        today = datetime.now().strftime("%Y-%m-%d")
        usage_key = f"{self.usage_key}:{today}"
        
        usage_data = self.redis.hgetall(usage_key)
        total_cost = 0.0
        
        for entry in usage_data.values():
            try:
                metrics = json.loads(entry)
                total_cost += metrics.get("cost_usd", 0.0)
            except:
                continue
        
        return total_cost
    
    def should_use_sonnet(
        self,
        complexity: TaskComplexity,
        force_model: Optional[str] = None
    ) -> bool:
        """
        Determine if Sonnet should be used based on complexity and constraints.
        
        Returns:
            bool: True for Sonnet, False for Haiku
        """
        # Allow manual override
        if force_model:
            return force_model.lower() == "sonnet"
        
        # Test mode always uses Haiku
        if self.config.get("test_mode"):
            logger.info("Test mode active - using Haiku")
            return False
        
        # Critical complexity always uses Sonnet
        if complexity == TaskComplexity.CRITICAL:
            return True
        
        # Check daily cost threshold
        daily_cost = self.get_daily_cost()
        if daily_cost > self.config["force_haiku_under_cost"]:
            logger.warning(f"Daily cost ${daily_cost:.2f} exceeds threshold - forcing Haiku")
            return False
        
        # Simple tasks always use Haiku
        if complexity == TaskComplexity.SIMPLE:
            return False
        
        # Complex tasks use Sonnet if under threshold
        if complexity == TaskComplexity.COMPLEX:
            return daily_cost < self.cost_threshold_daily * 0.7
        
        # Moderate tasks use Sonnet occasionally
        if complexity == TaskComplexity.MODERATE:
            # Use Sonnet 20% of the time for moderate tasks
            import random
            return random.random() < 0.2
        
        return False
    
    def record_usage(
        self,
        model: str,
        complexity: str,
        tokens_in: int,
        tokens_out: int,
        response_time_ms: float,
        task_type: str,
        success: bool = True
    ):
        """Record model usage for analytics and cost tracking"""
        # Calculate cost
        pricing = self.PRICING.get(model, self.PRICING["haiku"])
        cost = (tokens_in * pricing["input"] + tokens_out * pricing["output"]) / 1_000_000
        
        # Create metrics object
        metrics = ModelUsageMetrics(
            timestamp=datetime.now(),
            model=model,
            complexity=complexity,
            tokens_in=tokens_in,
            tokens_out=tokens_out,
            cost_usd=cost,
            response_time_ms=response_time_ms,
            task_type=task_type,
            success=success
        )
        
        # Store in Redis with daily partitioning
        today = datetime.now().strftime("%Y-%m-%d")
        usage_key = f"{self.usage_key}:{today}"
        
        # Store with timestamp as field
        timestamp = datetime.now().isoformat()
        self.redis.hset(
            usage_key,
            timestamp,
            json.dumps(asdict(metrics), default=str)
        )
        
        # Set expiry for 30 days
        self.redis.expire(usage_key, 30 * 24 * 3600)
        
        # Update running totals
        self._update_totals(model, cost)
        
        logger.info(
            f"Model usage recorded: {model} | Complexity: {complexity} | "
            f"Cost: ${cost:.4f} | Time: {response_time_ms:.0f}ms"
        )
    
    def _update_totals(self, model: str, cost: float):
        """Update running totals for quick access"""
        today = datetime.now().strftime("%Y-%m-%d")
        
        # Update daily totals
        self.redis.hincrby(f"lyco:daily_totals:{today}", f"{model}_count", 1)
        self.redis.hincrbyfloat(f"lyco:daily_totals:{today}", f"{model}_cost", cost)
        self.redis.hincrbyfloat(f"lyco:daily_totals:{today}", "total_cost", cost)
        
        # Set expiry
        self.redis.expire(f"lyco:daily_totals:{today}", 7 * 24 * 3600)
    
    def get_usage_stats(self, days: int = 7) -> Dict[str, Any]:
        """Get usage statistics for the specified number of days"""
        stats = {
            "by_day": {},
            "totals": {
                "haiku_count": 0,
                "sonnet_count": 0,
                "total_cost": 0.0,
                "haiku_cost": 0.0,
                "sonnet_cost": 0.0
            },
            "average_response_time": {
                "haiku": [],
                "sonnet": []
            }
        }
        
        for i in range(days):
            date = (datetime.now() - timedelta(days=i)).strftime("%Y-%m-%d")
            daily_totals = self.redis.hgetall(f"lyco:daily_totals:{date}")
            
            if daily_totals:
                day_stats = {}
                for key, value in daily_totals.items():
                    key = key.decode() if isinstance(key, bytes) else key
                    value = value.decode() if isinstance(value, bytes) else value
                    
                    if "count" in key:
                        day_stats[key] = int(value)
                        if "haiku" in key:
                            stats["totals"]["haiku_count"] += int(value)
                        elif "sonnet" in key:
                            stats["totals"]["sonnet_count"] += int(value)
                    else:
                        day_stats[key] = float(value)
                        if "haiku" in key:
                            stats["totals"]["haiku_cost"] += float(value)
                        elif "sonnet" in key:
                            stats["totals"]["sonnet_cost"] += float(value)
                        elif key == "total_cost":
                            stats["totals"]["total_cost"] += float(value)
                
                stats["by_day"][date] = day_stats
        
        return stats
    
    def update_config(self, **kwargs):
        """Update routing configuration"""
        self.config.update(kwargs)
        self.redis.set(self.config_key, json.dumps(self.config))
        logger.info(f"Model router config updated: {kwargs}")
    
    def set_test_mode(self, enabled: bool):
        """Enable/disable test mode (forces Haiku)"""
        self.update_config(test_mode=enabled)
        logger.info(f"Test mode {'enabled' if enabled else 'disabled'}")
