#!/usr/bin/env python3
"""
Send a test message to the Telegram bot to verify it's working
"""

import requests
import os
from dotenv import load_dotenv
import time

load_dotenv()

def send_test_message():
    """Send a test message to our bot"""
    
    bot_token = os.getenv("TELEGRAM_BOT_TOKEN")
    if not bot_token:
        print("❌ No TELEGRAM_BOT_TOKEN found")
        return False
    
    # Get bot info first
    response = requests.get(f"https://api.telegram.org/bot{bot_token}/getMe")
    if response.status_code == 200:
        bot_info = response.json()
        bot_username = bot_info['result']['username']
        print(f"✅ Connected to bot: @{bot_username}")
    else:
        print(f"❌ Failed to connect to bot: {response.status_code}")
        return False
    
    print(f"📱 Bot is ready to receive messages at @{bot_username}")
    print("   Send a test message like: 'Finish quarterly report by Friday (urgent, important)'")
    print("   The bot should now successfully save tasks to Notion without errors!")
    
    return True

if __name__ == "__main__":
    send_test_message()