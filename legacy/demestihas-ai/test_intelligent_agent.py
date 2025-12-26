#!/usr/bin/env python3
"""
Test script for the intelligent agent.
Run this to verify everything works before integrating with Telegram.
"""

import os
import sys
import asyncio
import logging
from dotenv import load_dotenv
import redis

# Add bot directory to path
sys.path.insert(0, '/root/lyco-ai')

# Load environment variables
load_dotenv()

# Configure logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

async def test_agent():
    """Test the intelligent agent with sample messages"""
    
    # Check required environment variables
    required_vars = {
        "ANTHROPIC_API_KEY": os.getenv("ANTHROPIC_API_KEY"),
        "NOTION_TOKEN": os.getenv("NOTION_TOKEN") or os.getenv("NOTION_API_KEY"),
        "NOTION_DATABASE_ID": os.getenv("NOTION_DATABASE_ID")
    }
    
    missing = [k for k, v in required_vars.items() if not v]
    if missing:
        logger.error(f"Missing environment variables: {missing}")
        logger.info("Please set these in your .env file")
        return
    
    # Set up Redis
    try:
        redis_client = redis.from_url(os.getenv("REDIS_URL", "redis://localhost:6379"))
        redis_client.ping()
        logger.info("✅ Redis connected")
    except Exception as e:
        logger.error(f"❌ Redis connection failed: {e}")
        logger.info("Continuing without Redis (no memory/stats)")
        redis_client = None
    
    # Import the agent
    try:
        from bot.agents.core.intelligent_agent import LycoIntelligentAgent
        logger.info("✅ Agent module imported")
    except ImportError as e:
        logger.error(f"❌ Failed to import agent: {e}")
        logger.info("Make sure you've created all the required files")
        return
    
    # Initialize the agent in test mode
    logger.info("Initializing intelligent agent in TEST MODE...")
    
    agent = LycoIntelligentAgent(
        anthropic_api_key=required_vars["ANTHROPIC_API_KEY"],
        notion_token=required_vars["NOTION_TOKEN"],
        notion_database_id=required_vars["NOTION_DATABASE_ID"],
        redis_client=redis_client,
        test_mode=True  # Start in test mode
    )
    
    logger.info("✅ Agent initialized successfully!")
    
    # Test messages
    test_messages = [
        "Buy milk and eggs",
        "Schedule dentist appointment for next week",
        "Have Viola pick up Stelios from soccer practice at 4pm",
        "Plan family dinner for Saturday, need to coordinate with everyone",
        "Urgent: Review Q3 budget report before meeting tomorrow at 2pm"
    ]
    
    print("\n" + "="*60)
    print("TESTING INTELLIGENT AGENT (Test Mode - No Notion Changes)")
    print("="*60 + "\n")
    
    for i, message in enumerate(test_messages, 1):
        print(f"\n[Test {i}] Message: {message}")
        print("-" * 40)
        
        try:
            response, metadata = await agent.process_message(
                message=message,
                user_id="test_user",
                user_context={"name": "Mene", "role": "parent"}
            )
            
            print(f"Response: {response}")
            print(f"Model Used: {metadata.get('model_used', 'unknown')}")
            print(f"Complexity: {metadata.get('complexity', 'unknown')}")
            print(f"Time: {metadata.get('duration_ms', 0):.0f}ms")
            
        except Exception as e:
            print(f"Error: {e}")
    
    # Show usage stats if Redis is available
    if redis_client:
        print("\n" + "="*60)
        print("USAGE STATISTICS")
        print("="*60)
        
        stats = agent.get_usage_stats(days=1)
        totals = stats["totals"]
        
        print(f"Total Requests: {totals['haiku_count'] + totals['sonnet_count']}")
        print(f"Haiku: {totals['haiku_count']} requests (${totals['haiku_cost']:.4f})")
        print(f"Sonnet: {totals['sonnet_count']} requests (${totals['sonnet_cost']:.4f})")
        print(f"Total Cost: ${totals['total_cost']:.4f}")

if __name__ == "__main__":
    print("Starting intelligent agent test...")
    asyncio.run(test_agent())
    print("\nTest complete!")
