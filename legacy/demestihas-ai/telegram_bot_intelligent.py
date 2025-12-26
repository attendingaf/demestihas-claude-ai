#!/usr/bin/env python3
"""
Intelligent Telegram Bot for Lyco.ai
Uses LangChain and Anthropic for natural language task processing.
"""

import os
import logging
import asyncio
from dotenv import load_dotenv
from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes

# Load environment variables
load_dotenv()

# Configure logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# Import our intelligent processor
from intelligent_task_processor import IntelligentTaskProcessor

# Global processor instance
processor = None

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Send a message when the command /start is issued."""
    await update.message.reply_text(
        "🏛️ Welcome to Lycurgus!\n\n"
        "I'm your ADHD-optimized task assistant. Just send me your tasks in natural language:\n\n"
        "• 'Buy groceries'\n"
        "• 'Schedule dentist next week'\n"
        "• 'Have Viola pick up kids'\n\n"
        "I'll organize them using the Eisenhower Matrix and add them to Notion.\n\n"
        "Commands:\n"
        "/start - Show this message\n"
        "/test - Toggle test mode (no Notion changes)\n"
        "/help - Get help"
    )

async def test_mode(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Toggle test mode on/off"""
    global processor
    processor.test_mode = not processor.test_mode
    status = "ON (no Notion changes)" if processor.test_mode else "OFF (creating real tasks)"
    await update.message.reply_text(f"Test mode is now {status}")

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle incoming messages and process them as tasks."""
    global processor
    
    # Get the message text
    message_text = update.message.text
    user_name = update.effective_user.first_name
    
    # Send typing indicator
    await update.message.chat.send_chat_action("typing")
    
    try:
        # Process the message
        response, metadata = processor.process_message(message_text)
        
        # Add test mode indicator if active
        if processor.test_mode:
            response = f"[TEST MODE]\n{response}"
        
        # Send response
        await update.message.reply_text(response)
        
        # Log the interaction
        logger.info(
            f"User: {user_name} | Tasks: {metadata.get('tasks_created', 0)} | "
            f"Time: {metadata.get('duration_ms', 0):.0f}ms"
        )
        
    except Exception as e:
        logger.error(f"Error processing message: {e}")
        await update.message.reply_text(
            "I encountered an error processing your message. Please try again."
        )

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Send a message when the command /help is issued."""
    help_text = """
🏛️ **Lycurgus Help**

**How to use:**
Just send me tasks in natural language! I'll automatically:
• Categorize them (Do Now, Schedule, Delegate, etc.)
• Estimate time and energy required
• Assign to family members when mentioned
• Add context tags

**Examples:**
• "Buy milk" → Quick errand
• "Review Q3 report" → Deep work task
• "Viola pickup kids 3pm" → Delegated task
• "Plan family dinner Saturday" → Scheduled event

**Family members:**
• Mene (you), Cindy (wife)
• Viola (au pair)
• Persy (11), Stelios (8), Franci (5)

**Commands:**
/start - Welcome message
/test - Toggle test mode
/help - This help message
    """
    await update.message.reply_text(help_text)

def main():
    """Start the bot."""
    global processor
    
    # Check required environment variables
    required = ["TELEGRAM_BOT_TOKEN", "ANTHROPIC_API_KEY", "NOTION_TOKEN", "NOTION_DATABASE_ID"]
    missing = [var for var in required if not os.getenv(var)]
    
    if missing:
        logger.error(f"Missing environment variables: {missing}")
        return
    
    # Initialize the intelligent processor
    logger.info("Initializing intelligent task processor...")
    processor = IntelligentTaskProcessor(
        anthropic_key=os.getenv("ANTHROPIC_API_KEY"),
        notion_token=os.getenv("NOTION_TOKEN"),
        notion_db_id=os.getenv("NOTION_DATABASE_ID"),
        test_mode=True  # Start in test mode for safety
    )
    logger.info("Processor initialized in TEST MODE")
    
    # Create the Application
    application = Application.builder().token(os.getenv("TELEGRAM_BOT_TOKEN")).build()
    
    # Register handlers
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("help", help_command))
    application.add_handler(CommandHandler("test", test_mode))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    
    # Run the bot
    logger.info("Starting Telegram bot...")
    application.run_polling()

if __name__ == "__main__":
    main()
