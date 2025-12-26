#!/usr/bin/env python3
"""
Diagnostic script to test telegram bot initialization
"""

import sys
import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

print("Testing Telegram Bot initialization...")
print("-" * 40)

# Check telegram module
try:
    import telegram
    print(f"✓ telegram module imported")
    print(f"  Version: {telegram.__version__}")
except ImportError as e:
    print(f"✗ Failed to import telegram: {e}")
    sys.exit(1)

# Check telegram.ext
try:
    from telegram.ext import Application, CommandHandler, MessageHandler, ContextTypes, filters
    print(f"✓ telegram.ext modules imported")
except ImportError as e:
    print(f"✗ Failed to import telegram.ext: {e}")
    sys.exit(1)

# Test token
bot_token = os.getenv("TELEGRAM_BOT_TOKEN")
if bot_token:
    print(f"✓ Bot token found (length: {len(bot_token)})")
else:
    print("✗ Bot token not found")
    sys.exit(1)

# Test creating Application
print("\nTesting Application creation...")
try:
    # Try the new v20+ way
    application = Application.builder().token(bot_token).build()
    print("✓ Application created successfully")
    
    # Test adding a simple handler
    async def start_command(update, context):
        pass
    
    application.add_handler(CommandHandler("start", start_command))
    print("✓ Handler added successfully")
    
except Exception as e:
    print(f"✗ Failed to create Application: {e}")
    print(f"  Error type: {type(e).__name__}")
    
    # Try alternative initialization
    print("\nTrying alternative initialization...")
    try:
        from telegram.ext import ApplicationBuilder
        application = ApplicationBuilder().token(bot_token).build()
        print("✓ Alternative initialization worked")
    except Exception as e2:
        print(f"✗ Alternative also failed: {e2}")

print("\n" + "-" * 40)
print("Diagnostic complete.")
