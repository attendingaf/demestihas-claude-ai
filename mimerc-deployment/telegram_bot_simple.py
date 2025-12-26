#!/usr/bin/env python3
"""
MiMerc Telegram Bot - Simple API Client Version
Connects to the MiMerc API service
"""

import os
import logging
import asyncio
import httpx
import json
from telegram import Update, Bot
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes

# Enable logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# Configuration
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
API_BASE_URL = os.getenv("API_BASE_URL", "http://agent:8000")

if not TELEGRAM_BOT_TOKEN:
    raise ValueError("TELEGRAM_BOT_TOKEN environment variable is not set")

# User thread mapping (telegram user id -> thread id)
user_threads = {}

async def call_api(message: str, thread_id: str) -> str:
    """Call the MiMerc API."""
    try:
        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{API_BASE_URL}/chat",
                json={"message": message, "thread_id": thread_id},
                headers={"Content-Type": "application/json"},
                timeout=10.0
            )
            if response.status_code == 200:
                data = response.json()
                return data.get("response", "I couldn't process that request.")
            else:
                logger.error(f"API returned status {response.status_code}")
                return "Sorry, I'm having trouble connecting to the service. Please try again later."
    except Exception as e:
        logger.error(f"Error calling API: {str(e)}")
        return "Sorry, I'm having trouble processing your request. Please try again later."

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Send a message when the command /start is issued."""
    user = update.effective_user
    await update.message.reply_text(
        f"Hello {user.first_name}! 👋\n\n"
        "I'm MiMerc, your grocery list management bot. I can help you:\n"
        "• Add items to your grocery list\n"
        "• Remove items from your list\n"
        "• Show your current list\n"
        "• Clear your entire list\n\n"
        "Just send me a message with what you'd like to do!\n\n"
        "Examples:\n"
        "- 'Add milk and eggs'\n"
        "- 'Remove bread'\n"
        "- 'Show my list'\n"
        "- 'Clear my list'"
    )

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Send a message when the command /help is issued."""
    await update.message.reply_text(
        "🛒 *MiMerc Commands*\n\n"
        "*Managing your list:*\n"
        "• Add items: 'Add [items]'\n"
        "• Remove items: 'Remove [items]'\n"
        "• View list: 'Show list' or 'What's on my list?'\n"
        "• Clear list: 'Clear list'\n\n"
        "*Commands:*\n"
        "/start - Welcome message\n"
        "/help - Show this help\n"
        "/list - Show your current grocery list\n"
        "/clear - Clear your entire list\n\n"
        "Just type naturally - I'll understand!",
        parse_mode='Markdown'
    )

async def show_list(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Show the current grocery list."""
    user_id = str(update.effective_user.id)
    thread_id = user_threads.get(user_id, f"telegram_{user_id}")

    response = await call_api("Show my grocery list", thread_id)
    await update.message.reply_text(response)

async def clear_list(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Clear the grocery list."""
    user_id = str(update.effective_user.id)
    thread_id = user_threads.get(user_id, f"telegram_{user_id}")

    response = await call_api("Clear my entire grocery list", thread_id)
    await update.message.reply_text(response)

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle regular messages."""
    user_id = str(update.effective_user.id)

    # Create or get thread ID for this user
    if user_id not in user_threads:
        user_threads[user_id] = f"telegram_{user_id}"

    thread_id = user_threads[user_id]
    message = update.message.text

    # Call the API
    response = await call_api(message, thread_id)

    # Send response
    await update.message.reply_text(response)

async def error_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Log errors."""
    logger.error(f"Update {update} caused error {context.error}")
    if update and update.message:
        await update.message.reply_text(
            "Sorry, an error occurred while processing your request. Please try again."
        )

def main():
    """Start the bot."""
    # Create the Application
    application = Application.builder().token(TELEGRAM_BOT_TOKEN).build()

    # Register handlers
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("help", help_command))
    application.add_handler(CommandHandler("list", show_list))
    application.add_handler(CommandHandler("clear", clear_list))

    # Handle all other messages
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))

    # Register error handler
    application.add_error_handler(error_handler)

    # Test API connection
    logger.info(f"Connecting to API at {API_BASE_URL}")

    # Start the bot
    logger.info("Starting MiMerc Telegram Bot...")
    application.run_polling(allowed_updates=Update.ALL_TYPES)

if __name__ == '__main__':
    main()
