#!/usr/bin/env python3
"""
MiMerc Telegram Bot - SHARED LIST VERSION
All users share a single grocery list via unified thread_id
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

# CRITICAL CHANGE: Single shared thread for all users
SHARED_THREAD_ID = "shared_family_list"  # All users use this same thread

if not TELEGRAM_BOT_TOKEN:
    raise ValueError("TELEGRAM_BOT_TOKEN environment variable is not set")

async def call_api(message: str, user_name: str = "User") -> str:
    """
    Call the MiMerc API with shared thread.
    MODIFIED: Always uses SHARED_THREAD_ID instead of per-user threads
    """
    try:
        # Add user context to the message for attribution
        contextualized_message = f"[{user_name}]: {message}"

        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{API_BASE_URL}/chat",
                json={
                    "message": contextualized_message,
                    "thread_id": SHARED_THREAD_ID  # CRITICAL: Always use shared thread
                },
                headers={"Content-Type": "application/json"},
                timeout=10.0
            )
            if response.status_code == 200:
                data = response.json()
                # Add user attribution to response for clarity
                response_text = data.get("response", "I couldn't process that request.")
                return f"✅ {response_text}\n\n_This is our shared family list._"
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
        "🛒 Welcome to the SHARED Family Grocery List!\n\n"
        "⚠️ **Important**: This is a SHARED list that ALL family members can see and edit.\n\n"
        "I can help you:\n"
        "• Add items to our shared list\n"
        "• Remove items from the list\n"
        "• Edit item quantities\n"
        "• Show the current shared list\n\n"
        "Examples:\n"
        "- 'Add \"chocolate syrup\" and milk'\n"
        "- 'Change milk quantity to 2 gallons'\n"
        "- 'Remove bread'\n"
        "- 'Show our list'\n\n"
        "_Remember: All changes are visible to everyone!_"
    )

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Send a message when the command /help is issued."""
    await update.message.reply_text(
        "🛒 *MiMerc SHARED List Commands*\n\n"
        "*Managing our shared list:*\n"
        "• Add items: 'Add [items]'\n"
        "• Edit quantity: 'Change [item] to [quantity]'\n"
        "• Remove items: 'Remove [items]'\n"
        "• View list: 'Show list' or 'What's on our list?'\n"
        "• Clear list: 'Clear entire list' (⚠️ affects everyone!)\n\n"
        "*Commands:*\n"
        "/start - Welcome message\n"
        "/help - Show this help\n"
        "/list - Show shared grocery list\n"
        "/who - See who's using the list\n\n"
        "*Pro tip*: Use quotes for multi-word items like \"chocolate syrup\"",
        parse_mode='Markdown'
    )

async def show_list(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Show the current SHARED grocery list."""
    user_name = update.effective_user.first_name or "User"

    response = await call_api("Show the complete grocery list", user_name)
    await update.message.reply_text(response, parse_mode='Markdown')

async def who_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Show information about the shared list."""
    await update.message.reply_text(
        "👥 *Shared List Information*\n\n"
        f"Thread ID: `{SHARED_THREAD_ID}`\n"
        "Status: 🟢 Active\n\n"
        "This list is shared by all users in this chat.\n"
        "Every addition, edit, or removal affects everyone!",
        parse_mode='Markdown'
    )

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Handle regular messages.
    MODIFIED: Routes all messages to shared thread with user attribution
    """
    user_name = update.effective_user.first_name or "User"
    message = update.message.text

    # Log who is making changes for transparency
    logger.info(f"User {user_name} (ID: {update.effective_user.id}) modifying shared list: {message}")

    # Call the API with shared thread
    response = await call_api(message, user_name)

    # Send response with markdown support
    await update.message.reply_text(response, parse_mode='Markdown')

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
    application.add_handler(CommandHandler("who", who_command))

    # Handle all other messages
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))

    # Register error handler
    application.add_error_handler(error_handler)

    # Log startup information
    logger.info(f"Starting MiMerc SHARED LIST Bot")
    logger.info(f"API endpoint: {API_BASE_URL}")
    logger.info(f"Shared thread ID: {SHARED_THREAD_ID}")

    # Start the bot
    application.run_polling(allowed_updates=Update.ALL_TYPES)

if __name__ == '__main__':
    main()
