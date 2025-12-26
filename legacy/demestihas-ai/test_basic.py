#!/usr/bin/env python3
"""
Basic test to verify environment and imports
"""

import os
import sys
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

print("Testing environment setup...")
print("="*50)

# Check environment variables
env_vars = {
    "TELEGRAM_BOT_TOKEN": os.getenv("TELEGRAM_BOT_TOKEN"),
    "ANTHROPIC_API_KEY": os.getenv("ANTHROPIC_API_KEY"),
    "NOTION_TOKEN": os.getenv("NOTION_TOKEN") or os.getenv("NOTION_API_KEY"),
    "NOTION_DATABASE_ID": os.getenv("NOTION_DATABASE_ID"),
    "REDIS_URL": os.getenv("REDIS_URL", "redis://localhost:6379")
}

print("\nEnvironment Variables:")
for key, value in env_vars.items():
    if value:
        print(f"✅ {key}: {'Set' if key != 'REDIS_URL' else value}")
    else:
        print(f"❌ {key}: Missing")

print("\nTesting imports...")
try:
    import redis
    print("✅ redis imported")
except ImportError as e:
    print(f"❌ redis: {e}")

try:
    import langchain
    print(f"✅ langchain imported (version: {langchain.__version__})")
except ImportError as e:
    print(f"❌ langchain: {e}")

try:
    from langchain_anthropic import ChatAnthropic
    print("✅ langchain_anthropic imported")
except ImportError as e:
    print(f"❌ langchain_anthropic: {e}")

try:
    from notion_client import Client
    print("✅ notion_client imported")
except ImportError as e:
    print(f"❌ notion_client: {e}")

# Test Redis connection
print("\nTesting Redis connection...")
try:
    import redis
    r = redis.from_url(os.getenv("REDIS_URL", "redis://localhost:6379"))
    r.ping()
    print("✅ Redis connected successfully")
except Exception as e:
    print(f"❌ Redis connection failed: {e}")

# Test Notion connection
print("\nTesting Notion connection...")
if env_vars["NOTION_TOKEN"] and env_vars["NOTION_DATABASE_ID"]:
    try:
        from notion_client import Client
        notion = Client(auth=env_vars["NOTION_TOKEN"])
        db_info = notion.databases.retrieve(database_id=env_vars["NOTION_DATABASE_ID"])
        print(f"✅ Notion connected: {db_info.get('title', [{}])[0].get('text', {}).get('content', 'Unknown')}")
    except Exception as e:
        print(f"❌ Notion connection failed: {e}")
else:
    print("⚠️  Skipping Notion test (missing credentials)")

print("\n" + "="*50)
print("Setup test complete!")
