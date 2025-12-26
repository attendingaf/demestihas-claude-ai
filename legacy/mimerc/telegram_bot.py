#!/usr/bin/env python3
"""
MiMerc Telegram Bot - ENHANCED UI VERSION
All users share a single grocery list with user initial tags [M], [J], etc.
Works in both private chats and group chats
"""

import os
import logging
import asyncio
import httpx
import json
from typing import Optional
from telegram import Update, Bot, InlineKeyboardButton, InlineKeyboardMarkup, CallbackQuery
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes, CallbackQueryHandler

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

# Bot username for group mentions (will be set on startup)
BOT_USERNAME = None

if not TELEGRAM_BOT_TOKEN:
    raise ValueError("TELEGRAM_BOT_TOKEN environment variable is not set")

def create_simple_keyboard():
    """Create simple inline keyboard with only Show List and Clear All"""
    keyboard = [
        [
            InlineKeyboardButton("📋 Show List", callback_data="action_show"),
            InlineKeyboardButton("🗑️ Clear All", callback_data="action_clear")
        ]
    ]
    return InlineKeyboardMarkup(keyboard)

async def call_api(message: str, user_name: str = "User", user_initial: str = "") -> tuple[str, list]:
    """
    Call the MiMerc API with shared thread and user initial.
    Returns (response_text, grocery_list)
    """
    try:
        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{API_BASE_URL}/chat",
                json={
                    "message": message,
                    "thread_id": SHARED_THREAD_ID,
                    "user_name": user_name,
                    "user_initial": user_initial
                },
                headers={"Content-Type": "application/json"},
                timeout=10.0
            )
            if response.status_code == 200:
                data = response.json()
                return data.get("response", "I couldn't process that request."), data.get("grocery_list", [])
            else:
                logger.error(f"API returned status {response.status_code}")
                return "Sorry, I'm having trouble connecting to the service. Please try again later.", []
    except Exception as e:
        logger.error(f"Error calling API: {str(e)}")
        return "Sorry, I'm having trouble processing your request. Please try again later.", []

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Send a message when the command /start is issued."""
    user = update.effective_user
    chat_type = update.message.chat.type

    welcome_text = (
        f"Hello {user.first_name}! 👋\n\n"
        "🛒 <b>Welcome to the SHARED Family Grocery List!</b>\n\n"
        "⚠️ <b>Important</b>: This is a SHARED list that ALL family members can see and edit.\n\n"
    )

    if chat_type in ['group', 'supergroup']:
        bot_name = BOT_USERNAME or 'mimercado_bot'
        welcome_text += (
            "<b>How to use in groups:</b>\n"
            f"• Mention me: @{bot_name} add milk\n"
            "• Reply to my messages\n"
            "• Use commands: /list, /help\n\n"
        )
    else:
        welcome_text += (
            "<b>How to use:</b>\n"
            "• Type naturally: 'Add milk and eggs'\n"
            "• Each item shows who added it with their initial\n"
            "• The list updates after every change\n\n"
        )

    welcome_text += "Ready to manage your shared grocery list?"

    await update.message.reply_text(
        welcome_text,
        parse_mode='HTML',
        reply_markup=create_simple_keyboard()
    )

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Send a message when the command /help is issued."""
    chat_type = update.message.chat.type

    help_text = (
        "🛒 <b>MiMerc SHARED List Help</b>\n\n"
        "<b>Natural Language Commands:</b>\n"
        "• 'Add milk and eggs'\n"
        "• 'Add 2 gallons of milk' <i>(quantity shown)</i>\n"
        "• 'Remove butter from the list'\n"
        "• 'What's on our list?'\n"
        "• 'Clear the entire list'\n\n"
    )

    if chat_type in ['group', 'supergroup']:
        bot_name = BOT_USERNAME or 'mimercado_bot'
        help_text += (
            "<b>In Group Chats:</b>\n"
            f"• Mention the bot: @{bot_name} add bread\n"
            "• Reply to bot messages\n"
            "• Use slash commands\n\n"
        )

    help_text += (
        "<b>Bot Commands:</b>\n"
        "/start - Welcome & buttons\n"
        "/help - Show this help\n"
        "/list - Show current list\n"
        "/add [items] - Add items to list\n"
        "/remove [items] - Remove items from list\n\n"
        "💡 <b>Notes:</b>\n"
        "• Each item shows [Initial] of who added it\n"
        "• Quantities only shown when specified\n"
        "• The list updates after each change!"
    )

    await update.message.reply_text(
        help_text,
        parse_mode='HTML',
        reply_markup=create_simple_keyboard()
    )

async def show_list(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Show the current SHARED grocery list."""
    user_name = update.effective_user.first_name or "User"
    user_initial = user_name[0].upper() if user_name else "U"

    response_text, grocery_list = await call_api("Show the complete grocery list", user_name, user_initial)

    await update.message.reply_text(
        response_text,
        parse_mode='HTML',
        reply_markup=create_simple_keyboard()
    )

async def add_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /add command"""
    user_name = update.effective_user.first_name or "User"
    user_initial = user_name[0].upper() if user_name else "U"
    message_text = update.message.text

    # In group chats, check if bot is mentioned or it's a reply to bot
    if update.message.chat.type in ['group', 'supergroup']:
        bot_username = context.bot.username
        # Check if message mentions the bot
        if f'@{bot_username}' in message_text:
            # Remove the bot mention from the message
            message_text = message_text.replace(f'@{bot_username}', '').strip()
        else:
            # In groups, only respond to messages that mention the bot or are replies to bot
            if not update.message.reply_to_message or update.message.reply_to_message.from_user.id != context.bot.id:
                return  # Don't respond if not mentioned and not a reply to bot


    # Get items from command arguments
    if context.args:
        items = ' '.join(context.args)
        message = f"Add {items}"

        logger.info(f"User {user_name} [{user_initial}] using /add command: {message}")

        response_text, grocery_list = await call_api(message, user_name, user_initial)

        await update.message.reply_text(
            response_text,
            parse_mode='HTML',
            reply_markup=create_simple_keyboard()
        )
    else:
        await update.message.reply_text(
            "Please specify items to add. Example: <code>/add milk and bread</code>",
            parse_mode='HTML'
        )
async def remove_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /remove command"""
    user_name = update.effective_user.first_name or "User"
    user_initial = user_name[0].upper() if user_name else "U"

    # Get items from command arguments
    if context.args:
        items = ' '.join(context.args)
        message = f"Remove {items}"

        logger.info(f"User {user_name} [{user_initial}] using /remove command: {message}")

        response_text, grocery_list = await call_api(message, user_name, user_initial)

        await update.message.reply_text(
            response_text,
            parse_mode='HTML',
            reply_markup=create_simple_keyboard()
        )
    else:
        await update.message.reply_text(
            "Please specify items to remove. Example: <code>/remove butter</code>",
            parse_mode='HTML'
        )
async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle regular text messages with enhanced UI"""
    if not update.message or not update.message.text:
        return

    user_name = update.effective_user.first_name or "User"
    user_initial = user_name[0].upper() if user_name else "U"
    message_text = update.message.text
    chat_type = update.message.chat.type

    # In group chats, only respond to mentions or replies
    if chat_type in ['group', 'supergroup']:
        # IMPORTANT: Due to Telegram privacy mode, the bot might not receive @mentions
        # Log to debug what we're receiving
        logger.info(f"DEBUG: Group message received - User: {user_name}, Text: {message_text[:50]}...")

        bot_username = BOT_USERNAME or context.bot.username
        is_mentioned = f'@{bot_username}' in message_text if bot_username else False
        is_reply_to_bot = (
            update.message.reply_to_message and
            update.message.reply_to_message.from_user.id == context.bot.id
        ) if update.message.reply_to_message else False

        if is_mentioned:
            # Remove the bot mention from the message
            message_text = message_text.replace(f'@{bot_username}', '').strip()
            logger.info(f"Bot mentioned in group by {user_name} [{user_initial}]: {message_text}")
        elif is_reply_to_bot:
            logger.info(f"Reply to bot in group by {user_name} [{user_initial}]: {message_text}")
        else:
            # In groups, ignore messages that don't mention the bot or reply to it
            logger.info(f"Ignoring group message (not mentioned/reply)")
            return
    else:
        # In private chats, process all messages
        logger.info(f"Private message from {user_name} [{user_initial}]: {message_text}")

    # Call the API with user initial
    response_text, grocery_list = await call_api(message_text, user_name, user_initial)



    # Send response with simple keyboard
    await update.message.reply_text(
        response_text,
        parse_mode='HTML',
        reply_markup=create_simple_keyboard()
    )

async def handle_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle inline keyboard button callbacks"""
    query = update.callback_query
    user_name = update.effective_user.first_name or "User"
    user_initial = user_name[0].upper() if user_name else "U"

    # Acknowledge the callback
    await query.answer()

    # Parse the callback data
    action = query.data

    # Handle different actions
    if action == "action_show":
        message = "Show the list"
    elif action == "action_clear":
        # Add confirmation for clear action
        confirm_keyboard = InlineKeyboardMarkup([
            [
                InlineKeyboardButton("⚠️ Yes, Clear All", callback_data="confirm_clear"),
                InlineKeyboardButton("❌ Cancel", callback_data="action_show")
            ]
        ])
        await query.edit_message_text(
            "⚠️ <b>Are you sure?</b>\n\nThis will clear the ENTIRE shared list for ALL family members!",
            parse_mode='HTML',
            reply_markup=confirm_keyboard
        )
        return
    elif action == "confirm_clear":
        message = "Clear the entire list"
    else:
        await query.edit_message_text("Unknown action. Please try again.")
        return

    # Call the API with the action
    response_text, grocery_list = await call_api(message, user_name, user_initial)

    # Update the message with new content and keyboard
    try:
        await query.edit_message_text(
            response_text,
            parse_mode='HTML',
            reply_markup=create_simple_keyboard()
        )
    except Exception as e:
        # If edit fails (e.g., message is too old), send a new message
        await query.message.reply_text(
            response_text,
            parse_mode='HTML',
            reply_markup=create_simple_keyboard()
        )

async def error_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Log errors and notify user"""
    logger.error(f"Update {update} caused error {context.error}")

    error_message = (
        "❌ Sorry, an error occurred while processing your request.\n"
        "Please try again or use /help for assistance."
    )

    if update and update.message:
        await update.message.reply_text(error_message)
    elif update and update.callback_query:
        await update.callback_query.answer("Error occurred. Please try again.", show_alert=True)

async def post_init(application: Application):
    """Initialize bot username after startup"""
    global BOT_USERNAME
    bot_info = await application.bot.get_me()
    BOT_USERNAME = bot_info.username
    logger.info(f"Bot username set to: @{BOT_USERNAME}")

def main():
    """Start the enhanced bot."""
    # Create the Application
    application = Application.builder().token(TELEGRAM_BOT_TOKEN).post_init(post_init).build()

    # Register command handlers
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("help", help_command))
    application.add_handler(CommandHandler("list", show_list))
    application.add_handler(CommandHandler("add", add_command))
    application.add_handler(CommandHandler("remove", remove_command))

    # Register callback query handler for inline keyboards
    application.add_handler(CallbackQueryHandler(handle_callback))

    # Handle all other text messages (both private and groups with mentions)
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))

    # Register error handler
    application.add_error_handler(error_handler)

    # Log startup information
    logger.info(f"Starting MiMerc ENHANCED UI Bot")
    logger.info(f"API endpoint: {API_BASE_URL}")
    logger.info(f"Shared thread ID: {SHARED_THREAD_ID}")
    logger.info("Features: Group chat support, user initials, smart quantity display")
    logger.info("Bot will work in groups when mentioned or via commands")

    # Start the bot
    application.run_polling(allowed_updates=Update.ALL_TYPES)

if __name__ == '__main__':
    main()
