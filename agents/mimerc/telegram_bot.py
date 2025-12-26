#!/usr/bin/env python3
"""
MiMerc Telegram Bot - Conversational Interface
A streamlined, conversational Telegram bot for the MiMerc grocery list agent.
This bot focuses on natural language interaction without complex commands.
"""

import os
import sys
import asyncio
import logging
import signal
from typing import Optional
import threading
from concurrent.futures import ThreadPoolExecutor

from telegram import Update, Bot
from telegram.ext import (
    Application,
    CommandHandler,
    MessageHandler,
    ContextTypes,
    filters
)
from telegram.constants import ParseMode, ChatAction

from langchain_core.messages import HumanMessage, AIMessage
from dotenv import load_dotenv

# Import the existing agent components
from agent import build_graph

# Load environment variables
load_dotenv()

# Configure logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# Global variables for resource management
graph = None
pool = None
executor = ThreadPoolExecutor(max_workers=5)  # For running sync code in async context

def initialize_agent():
    """Initialize the LangGraph agent and database pool"""
    global graph, pool
    try:
        logger.info("Initializing MiMerc agent and database connection...")
        graph, pool = build_graph()
        logger.info("Successfully initialized agent and database")
        return True
    except Exception as e:
        logger.error(f"Failed to initialize agent: {e}")
        return False

def run_agent_sync(text: str, thread_id: str) -> str:
    """
    Synchronous wrapper to run the LangGraph agent.
    This function runs in a thread pool executor to avoid blocking the async event loop.
    """
    try:
        # Create input state for the agent
        # CRITICAL FIX: Don't initialize grocery_list - let LangGraph load from checkpoint
        input_state = {
            "messages": [HumanMessage(content=text)],
            # Don't initialize grocery_list - checkpointer will load persisted state
            "final_response": "",  # Initialize final_response channel
            "tool_calls": [],
            "next_action": ""
        }

        # Configuration with thread ID for state persistence
        # Critical: Use chat_id as thread_id for conversation continuity
        config = {"configurable": {"thread_id": thread_id}}

        # Process through the LangGraph stream
        final_output = ""

        # FIX: Look ONLY for the final_response channel to avoid duplicates
        # Critical: Only capture the responder's final_response, ignore all other outputs
        for chunk in graph.stream(input_state, config):
            # Only process the responder node's output
            if "responder" in chunk:
                responder_output = chunk["responder"]
                # Check if this is a dict containing final_response
                if isinstance(responder_output, dict) and "final_response" in responder_output:
                    final_output = responder_output["final_response"]
                    break  # Exit immediately - we have the single definitive response

            # Do NOT accumulate or concatenate anything else

        return final_output if final_output else "I've processed your request."

    except Exception as e:
        logger.error(f"Error in agent processing: {e}")
        raise

async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """
    Handle the /start command.
    Provides a simple welcome message with conversational instructions.
    """
    user_name = update.effective_user.first_name or "there"
    welcome_message = (
        f"👋 Welcome to MiMerc, {user_name}!\n\n"
        "I'm your conversational grocery assistant. Just tell me what you need in plain language:\n\n"
        "• \"Add milk and eggs to my list\"\n"
        "• \"Remove bread\"\n"
        "• \"What's on my grocery list?\"\n"
        "• \"Add 2 pounds of chicken\"\n"
        "• \"Clear my list\"\n\n"
        "No commands needed - just chat naturally! 🛒"
    )

    await update.message.reply_text(
        welcome_message,
        parse_mode=ParseMode.MARKDOWN
    )

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """
    Core conversational handler for all non-command text messages.
    This is where the magic happens - natural language goes in, grocery management comes out.
    """
    # Extract the user's message
    user_message = update.message.text

    # Critical: Extract and convert chat_id to string for thread_id
    # This ensures conversation continuity per chat
    chat_id = str(update.effective_chat.id)
    thread_id = f"telegram_{chat_id}"

    # Log the interaction
    user_name = update.effective_user.username or update.effective_user.first_name
    logger.info(f"Processing message from {user_name} (thread: {thread_id}): {user_message[:50]}...")

    try:
        # Show typing indicator while processing
        await update.message.chat.send_action(ChatAction.TYPING)

        # Run the synchronous agent in a thread pool to avoid blocking
        loop = asyncio.get_event_loop()
        response = await loop.run_in_executor(
            executor,
            run_agent_sync,
            user_message,
            thread_id
        )

        # Format the response for better readability
        if response:
            # Add emojis based on content
            if "added" in response.lower():
                response = f"✅ {response}"
            elif "removed" in response.lower():
                response = f"🗑️ {response}"
            elif "list" in response.lower() and ("your" in response.lower() or "current" in response.lower()):
                # Format list display
                response = format_list_response(response)
            elif "cleared" in response.lower() or "empty" in response.lower():
                response = f"🧹 {response}"

            # Send the response back to the user
            await update.message.reply_text(
                response,
                parse_mode=ParseMode.MARKDOWN
            )
        else:
            # Fallback if no response
            await update.message.reply_text(
                "I understood your request and processed it. Try asking \"What's on my list?\" to see the current items."
            )

    except Exception as e:
        logger.error(f"Error handling message from {user_name}: {e}")

        # Send user-friendly error message
        error_message = (
            "😔 I'm sorry, I encountered an issue processing your request.\n"
            "Please try again in a moment. If the problem persists, try restarting with /start."
        )
        await update.message.reply_text(error_message)

def format_list_response(response: str) -> str:
    """
    Format the grocery list response for better Telegram display.
    Adds emojis and markdown formatting.
    """
    # Check if list is empty
    if "empty" in response.lower():
        return "📋 *Your Grocery List*\n\n_Your list is empty. Start adding items!_"

    # Format the list items
    lines = response.strip().split('\n')
    formatted = ["📋 *Your Grocery List*\n"]

    for line in lines:
        # Skip header lines
        if "list" in line.lower() and ":" in line:
            continue
        # Format bullet points
        cleaned = line.strip().lstrip('•').lstrip('-').strip()
        if cleaned:
            formatted.append(f"• {cleaned}")

    # If only header, list is empty
    if len(formatted) == 1:
        formatted.append("\n_Your list is empty._")

    return '\n'.join(formatted)

async def error_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """
    Handle errors that occur during update processing.
    """
    logger.error(f"Update {update} caused error: {context.error}")

    # Try to send error message to user
    try:
        if update and update.effective_message:
            await update.effective_message.reply_text(
                "⚠️ An unexpected error occurred. Please try again.",
                parse_mode=ParseMode.MARKDOWN
            )
    except Exception as e:
        logger.error(f"Failed to send error message: {e}")

def cleanup_resources():
    """
    Clean up resources on shutdown.
    Properly close database pool and executor.
    """
    global pool, executor

    logger.info("Cleaning up resources...")

    # Close the thread pool executor
    if executor:
        executor.shutdown(wait=True)
        logger.info("Thread pool executor closed")

    # Close database pool
    if pool:
        try:
            pool.close()
            logger.info("Database connection pool closed")
        except Exception as e:
            logger.error(f"Error closing database pool: {e}")

def signal_handler(signum, frame):
    """Handle shutdown signals gracefully"""
    logger.info(f"Received signal {signum}, initiating shutdown...")
    cleanup_resources()
    sys.exit(0)

def main():
    """
    Main function to run the Telegram bot.
    Sets up handlers and starts the bot polling loop.
    """
    # Register signal handlers for graceful shutdown
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)

    # Get bot token from environment
    bot_token = os.getenv("TELEGRAM_BOT_TOKEN")
    if not bot_token:
        logger.error("TELEGRAM_BOT_TOKEN not found in environment variables!")
        logger.error("Please set it in your .env file")
        logger.error("Get a token from @BotFather on Telegram")
        sys.exit(1)

    # Initialize the agent
    if not initialize_agent():
        logger.error("Failed to initialize agent, exiting...")
        sys.exit(1)

    try:
        # Create the Application
        logger.info("Creating Telegram bot application...")
        application = Application.builder().token(bot_token).build()

        # Add command handlers
        application.add_handler(CommandHandler("start", start_command))

        # Add the core conversational message handler
        # This handles ALL text messages that aren't commands
        application.add_handler(MessageHandler(
            filters.TEXT & ~filters.COMMAND,
            handle_message
        ))

        # Add error handler
        application.add_error_handler(error_handler)

        # Start the bot
        logger.info("Starting MiMerc Telegram Bot...")
        logger.info("Bot is ready! Send messages to interact.")
        logger.info("Press Ctrl+C to stop")

        # Run the bot until interrupted
        application.run_polling(
            allowed_updates=Update.ALL_TYPES,
            drop_pending_updates=True  # Ignore messages sent while bot was offline
        )

    except KeyboardInterrupt:
        logger.info("Received keyboard interrupt, shutting down...")
    except Exception as e:
        logger.error(f"Fatal error: {e}")
    finally:
        cleanup_resources()
        logger.info("Bot shutdown complete")

if __name__ == "__main__":
    main()
