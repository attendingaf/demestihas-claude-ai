#!/usr/bin/env python3
"""
Lyco Family Bot - Clean Rebuild
Minimal working version with core functionality
Date: September 1, 2025
"""

import os
import logging
import asyncio
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, MessageHandler, CallbackQueryHandler, filters, ContextTypes

# Configure logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# Environment variables
BOT_TOKEN = os.getenv('TELEGRAM_BOT_TOKEN')
if not BOT_TOKEN:
    logger.error("TELEGRAM_BOT_TOKEN not found in environment")
    exit(1)

async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /start command"""
    user = update.effective_user
    welcome_message = f"""
👋 Hi {user.first_name}! I'm Lyco, your family AI assistant.

🎯 **What I do:**
- Capture tasks and ideas
- Save them to Notion
- Help organize family life

📝 **How to use me:**
Just send me any message like:
- "Buy milk and bread"
- "Call dentist tomorrow"
- "Pick up kids at 3pm"

I'll extract the important details and save them for you!

Try sending me a task now! 🚀
"""
    await update.message.reply_text(welcome_message)

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle all text messages"""
    user = update.effective_user
    message_text = update.message.text
    
    logger.info(f"Message from {user.first_name}: {message_text}")
    
    # Simple task extraction (we'll enhance this later)
    task_details = {
        "task": message_text,
        "user": user.first_name,
        "priority": "medium",  # Default priority
        "status": "todo"
    }
    
    # Create response
    response = f"""✅ **Task Captured!**

📝 **Task:** {message_text}
👤 **From:** {user.first_name}
⚡ **Priority:** Medium
📅 **Status:** To Do

💾 **Next:** I'll save this to Notion (integration coming next)"""
    
    # Add action buttons
    keyboard = [
        [InlineKeyboardButton("✅ Mark Complete", callback_data=f"complete_{update.message.message_id}")],
        [InlineKeyboardButton("🔥 High Priority", callback_data=f"priority_high_{update.message.message_id}")],
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await update.message.reply_text(response, reply_markup=reply_markup)

async def button_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle button presses"""
    query = update.callback_query
    await query.answer()
    
    callback_data = query.data
    
    if callback_data.startswith("complete_"):
        await query.edit_message_text("✅ **Task marked as complete!**\n\n(Full functionality coming soon)")
    
    elif callback_data.startswith("priority_high_"):
        await query.edit_message_text("🔥 **Priority updated to HIGH!**\n\n(Full functionality coming soon)")

async def error_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle errors"""
    logger.error(f"Update {update} caused error {context.error}")
    
    if update and update.effective_message:
        await update.effective_message.reply_text(
            "😅 **Something went wrong!**\n\n"
            "I'm a simple bot right now, but I'm getting better every day!\n"
            "Try sending a simple task message."
        )

def main():
    """Start the bot"""
    logger.info("🚀 Starting Lyco Family Bot...")
    
    # Create application
    application = Application.builder().token(BOT_TOKEN).build()
    
    # Add handlers
    application.add_handler(CommandHandler("start", start_command))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    application.add_handler(CallbackQueryHandler(button_callback))
    application.add_error_handler(error_handler)
    
    logger.info("✅ Bot handlers configured")
    logger.info("🔄 Starting polling...")
    
    # Start the bot
    application.run_polling(allowed_updates=Update.ALL_TYPES)

if __name__ == '__main__':
    try:
        main()
    except KeyboardInterrupt:
        logger.info("👋 Bot stopped by user")
    except Exception as e:
        logger.error(f"💥 Bot crashed: {e}")
