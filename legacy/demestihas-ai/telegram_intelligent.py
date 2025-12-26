#!/usr/bin/env python3
"""
Lyco Intelligent Telegram Bot
"""

import os
import logging
import asyncio
from dotenv import load_dotenv
from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes

# Load environment
load_dotenv()

# Configure logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# Import our processor
from simple_bot import SimpleTaskProcessor

# Global processor
processor = None

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "🏛️ **Welcome to Lycurgus!**\n\n"
        "I'm your intelligent ADHD-optimized task assistant.\n\n"
        "Just send me tasks in natural language:\n"
        "• Buy groceries\n"
        "• Schedule dentist\n"
        "• Have Viola pick up kids\n\n"
        "Commands:\n"
        "/test - Toggle test mode\n"
        "/status - Check current mode\n"
        "/help - Show help"
    )

async def toggle_test(update: Update, context: ContextTypes.DEFAULT_TYPE):
    global processor
    processor.test_mode = not processor.test_mode
    status = "ON (no Notion changes)" if processor.test_mode else "OFF (creating real tasks)"
    await update.message.reply_text(f"✅ Test mode is now {status}")

async def status(update: Update, context: ContextTypes.DEFAULT_TYPE):
    global processor
    mode = "TEST MODE" if processor.test_mode else "PRODUCTION MODE"
    await update.message.reply_text(
        f"🏛️ **Lycurgus Status**\n\n"
        f"Mode: {mode}\n"
        f"Database: Connected\n"
        f"AI: Claude Haiku"
    )

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    global processor
    
    # Send typing indicator
    await update.message.chat.send_chat_action("typing")
    
    try:
        # Process message
        response, metadata = processor.process_message(update.message.text)
        
        # Send response
        await update.message.reply_text(response)
        
        # Log
        user = update.effective_user.first_name
        tasks = metadata.get('tasks_created', 0)
        time = metadata.get('duration_ms', 0)
        logger.info(f"User: {user} | Tasks: {tasks} | Time: {time:.0f}ms")
        
    except Exception as e:
        logger.error(f"Error: {e}")
        await update.message.reply_text(
            "❌ I encountered an error. Please try again."
        )

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "🏛️ **Lycurgus Help**\n\n"
        "**How to use:**\n"
        "Send me tasks in natural language!\n\n"
        "**Examples:**\n"
        "• Buy milk → Quick errand\n"
        "• Review Q3 report → Deep work\n"
        "• Viola pickup kids 3pm → Delegated\n\n"
        "**Family:**\n"
        "• Mene & Cindy (parents)\n"
        "• Viola (au pair)\n"
        "• Persy (11), Stelios (8), Franci (5)\n\n"
        "**Commands:**\n"
        "/start - Welcome\n"
        "/test - Toggle test mode\n"
        "/status - Check status\n"
        "/help - This message"
    )

def main():
    global processor
    
    # Check environment
    required = ["TELEGRAM_BOT_TOKEN", "ANTHROPIC_API_KEY", "NOTION_TOKEN", "NOTION_DATABASE_ID"]
    missing = [v for v in required if not os.getenv(v)]
    
    if missing:
        logger.error(f"Missing environment variables: {missing}")
        return
    
    # Initialize processor
    logger.info("Initializing processor...")
    processor = SimpleTaskProcessor(test_mode=True)
    logger.info("Processor ready in TEST MODE")
    
    # Create application
    app = Application.builder().token(os.getenv("TELEGRAM_BOT_TOKEN")).build()
    
    # Add handlers
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("help", help_command))
    app.add_handler(CommandHandler("test", toggle_test))
    app.add_handler(CommandHandler("status", status))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    
    # Run bot
    logger.info("🚀 Starting Lycurgus bot...")
    logger.info("Bot username: @LycurgusBot")
    logger.info("Mode: TEST MODE (use /test to toggle)")
    app.run_polling()

if __name__ == "__main__":
    main()
