#!/usr/bin/env python3
"""
Yanay - Simplified Orchestrator
Routes Telegram messages to Lyco Eisenhower Matrix agent
Simplified version focusing only on task management
"""

import os
import logging
import asyncio
from typing import Optional

from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes
import sys
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(__file__))))

from agents.lyco.lyco_eisenhower import LycoEisenhowerAgent

logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)


class YanayOrchestrator:
    """Simple orchestrator for Lyco task management"""
    
    def __init__(self):
        self.telegram_token = os.getenv("TELEGRAM_BOT_TOKEN")
        if not self.telegram_token:
            raise ValueError("TELEGRAM_BOT_TOKEN not set")
        
        # Initialize Lyco agent
        self.lyco_agent = LycoEisenhowerAgent()
        
        # Track user context
        self.user_contexts = {}
        
        logger.info("Yanay orchestrator initialized")
    
    async def start_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /start command"""
        user_name = update.effective_user.first_name or "there"
        welcome_message = f"""👋 Hi {user_name}!

I'm Lycurgus, your family task manager. I help organize tasks using the Eisenhower Matrix.

**Quick Start:**
• Just type any task to add it
• Or say "Add task: [description]"
• "Show today" for your daily tasks
• "Show matrix" for all quadrants

Type "help" for more commands."""
        
        await update.message.reply_text(welcome_message, parse_mode='Markdown')
    
    async def help_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /help command"""
        help_text = self.lyco_agent._get_help_text()
        await update.message.reply_text(help_text, parse_mode='Markdown')
    
    async def handle_message(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle all text messages"""
        if not update.message or not update.message.text:
            return
        
        message = update.message.text
        user_id = update.effective_user.id
        user_name = self._get_user_name(update.effective_user.username)
        
        logger.info(f"Message from {user_name} ({user_id}): {message}")
        
        # Process message through Lyco
        try:
            response = self.lyco_agent.handle_message(message, user_name)
            await update.message.reply_text(response, parse_mode='Markdown')
        except Exception as e:
            logger.error(f"Error processing message: {e}")
            await update.message.reply_text(
                "❌ Sorry, I encountered an error. Please try again or type 'help'."
            )
    
    async def today_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /today command"""
        user_name = self._get_user_name(update.effective_user.username)
        tasks = self.lyco_agent.get_today_tasks(user_name)
        response = self.lyco_agent.format_task_list(tasks, "📅 Today's Tasks")
        await update.message.reply_text(response, parse_mode='Markdown')
    
    async def matrix_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /matrix command"""
        user_name = self._get_user_name(update.effective_user.username)
        quadrants = self.lyco_agent.get_tasks_by_quadrant(user_name)
        response = self.lyco_agent.format_matrix_display(quadrants)
        await update.message.reply_text(response, parse_mode='Markdown')
    
    async def week_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /week command"""
        tasks = self.lyco_agent.get_week_tasks()
        response = self.lyco_agent.format_task_list(tasks, "📅 This Week's Tasks")
        await update.message.reply_text(response, parse_mode='Markdown')
    
    def _get_user_name(self, username: Optional[str]) -> str:
        """Map Telegram username to family member"""
        username_map = {
            "menedemestihas": "mene",
            "cindyloo": "cindy",  # Replace with actual username
        }
        return username_map.get(username, "mene")
    
    def run(self):
        """Start the bot"""
        application = Application.builder().token(self.telegram_token).build()
        
        # Register handlers
        application.add_handler(CommandHandler("start", self.start_command))
        application.add_handler(CommandHandler("help", self.help_command))
        application.add_handler(CommandHandler("today", self.today_command))
        application.add_handler(CommandHandler("matrix", self.matrix_command))
        application.add_handler(CommandHandler("week", self.week_command))
        application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, self.handle_message))
        
        # Start polling
        logger.info("Starting Yanay orchestrator...")
        application.run_polling()


if __name__ == "__main__":
    try:
        orchestrator = YanayOrchestrator()
        orchestrator.run()
    except KeyboardInterrupt:
        logger.info("Shutting down...")
    except Exception as e:
        logger.error(f"Fatal error: {e}")
        raise