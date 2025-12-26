#!/usr/bin/env python3
"""
Lyco.ai Bot v6 - Production Ready with Redis Memory & Enhanced AI
"""

import os
import asyncio
import logging
import json
import redis.asyncio as redis
from datetime import datetime, timedelta
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, MessageHandler, CallbackQueryHandler, filters, ContextTypes
import aiohttp
from ai_task_parser import EnhancedTaskParser, FamilyMember

# Enhanced logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(funcName)s:%(lineno)d - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# Configuration
BOT_TOKEN = os.environ.get('TELEGRAM_BOT_TOKEN', '')
ANTHROPIC_API_KEY = os.environ.get('ANTHROPIC_API_KEY', '')
NOTION_TOKEN = os.environ.get('NOTION_TOKEN', '')
NOTION_DATABASE_ID = os.environ.get('NOTION_DATABASE_ID', '')
NOTION_VERSION = '2022-06-28'

# Initialize enhanced parser
task_parser = EnhancedTaskParser(ANTHROPIC_API_KEY) if ANTHROPIC_API_KEY else None

# Redis Memory System
class RedisMemory:
    """Redis-based conversation memory with 10-message context window"""
    
    def __init__(self, redis_url: str = "redis://lyco-redis:6379"):
        self.redis_url = redis_url
        self.redis_client = None
        self.max_messages = 10
        self.ttl_hours = 24
        
    async def connect(self):
        """Initialize Redis connection with pool"""
        try:
            self.redis_client = redis.from_url(
                self.redis_url,
                encoding="utf-8",
                decode_responses=True,
                max_connections=10,
                retry_on_timeout=True
            )
            await self.redis_client.ping()
            logger.info("✅ Redis memory connected successfully")
        except Exception as e:
            logger.error(f"❌ Redis connection failed: {e}")
            self.redis_client = None
    
    async def disconnect(self):
        """Close Redis connection"""
        if self.redis_client:
            await self.redis_client.close()
    
    def _get_key(self, chat_id: int) -> str:
        """Generate Redis key for chat conversation"""
        return f"chat:{chat_id}:messages"
    
    async def store_message(self, chat_id: int, message: str, user_name: str = "User") -> bool:
        """Store message in conversation history"""
        if not self.redis_client:
            return False
            
        try:
            key = self._get_key(chat_id)
            
            # Create message object
            message_obj = {
                "timestamp": datetime.now().isoformat(),
                "user": user_name,
                "content": message[:500]  # Truncate long messages
            }
            
            # Add to list (LPUSH for newest first)
            await self.redis_client.lpush(key, json.dumps(message_obj))
            
            # Trim to max_messages
            await self.redis_client.ltrim(key, 0, self.max_messages - 1)
            
            # Set TTL
            await self.redis_client.expire(key, self.ttl_hours * 3600)
            
            return True
            
        except Exception as e:
            logger.error(f"Failed to store message: {e}")
            return False
    
    async def get_context(self, chat_id: int) -> list:
        """Retrieve last 10 messages for context"""
        if not self.redis_client:
            return []
            
        try:
            key = self._get_key(chat_id)
            
            # Get messages (LRANGE newest to oldest)
            messages = await self.redis_client.lrange(key, 0, self.max_messages - 1)
            
            # Parse and reverse (oldest first for context)
            context = []
            for msg in reversed(messages):
                try:
                    context.append(json.loads(msg))
                except json.JSONDecodeError:
                    continue
                    
            return context
            
        except Exception as e:
            logger.error(f"Failed to get context: {e}")
            return []
    
    async def clear_context(self, chat_id: int) -> bool:
        """Clear conversation history for chat"""
        if not self.redis_client:
            return False
            
        try:
            key = self._get_key(chat_id)
            await self.redis_client.delete(key)
            return True
        except Exception as e:
            logger.error(f"Failed to clear context: {e}")
            return False

# Global memory instance
memory = None

# User session storage (now with Redis backup)
user_sessions = {}

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Enhanced start with family context"""
    user = update.effective_user
    chat_id = update.effective_chat.id
    
    # Clear conversation context for fresh start
    if memory:
        await memory.clear_context(chat_id)
    
    # Initialize user session
    user_sessions[user.id] = {
        'name': user.first_name,
        'tasks_today': 0,
        'last_energy_check': datetime.now(),
        'family_mode': False
    }
    
    keyboard = [
        [InlineKeyboardButton("📝 Quick Task", callback_data='quick_task')],
        [InlineKeyboardButton("👨‍👩‍👧‍👦 Family Mode", callback_data='family_mode')],
        [InlineKeyboardButton("⚡ Energy Check", callback_data='energy_check')],
        [InlineKeyboardButton("📊 Today's Tasks", callback_data='today_tasks')]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    welcome_message = f'''🧠 **Welcome to Lyco v6, {user.first_name}!**
    
I'm your ADHD-optimized task assistant with conversation memory.

**🎯 Core Features:**
• Natural language task capture
• Conversation context memory (10 messages)
• Auto-categorization (Eisenhower Matrix)
• Family member delegation
• Energy-based scheduling
• ADHD-friendly breakdowns

**👨‍👩‍👧‍👦 Family Members:**
• **Cindy** - Wife, physician
• **Viola** - Au pair (childcare/transport)
• **Persy** (11) - Oldest
• **Stelios** (8) - Middle
• **Franci** (5) - Youngest

**💬 Just send me any task or use the buttons below!**

Examples:
• "Buy groceries for dinner"
• "Ask Viola to pick up kids at 3pm"
• "Review budget report tomorrow"
• "Emergency: Call pediatrician now"

**🧠 Memory**: I'll remember our conversation to understand context!'''
    
    await update.message.reply_text(
        welcome_message,
        parse_mode='Markdown',
        reply_markup=reply_markup
    )

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Enhanced message handler with Redis memory and conversation context"""
    message = update.message
    chat_id = message.chat_id
    user = message.from_user
    user_id = user.id
    user_name = user.first_name or "User"
    text = message.text or ""
    
    logger.info(f"📝 Message from {user_name} (ID: {chat_id}): {text[:50]}...")
    
    # Update session
    if user_id not in user_sessions:
        user_sessions[user_id] = {'name': user_name, 'tasks_today': 0}
    
    user_sessions[user_id]['tasks_today'] += 1
    
    # Send typing indicator
    await context.bot.send_chat_action(chat_id=chat_id, action='typing')
    
    try:
        # Store incoming message in memory
        if memory:
            await memory.store_message(chat_id, text, user_name)
            conversation_context = await memory.get_context(chat_id)
        else:
            conversation_context = []
        
        # Build context for AI if we have conversation history
        context_text = ""
        if conversation_context and len(conversation_context) > 1:
            context_text = "Recent conversation:\n"
            # Include last 3 messages for context (excluding current)
            for msg in conversation_context[-4:-1]:  
                context_text += f"{msg['user']}: {msg['content']}\n"
            context_text += f"\nCurrent message from {user_name}:\n"
        
        full_message = f"{context_text}{text}"
        
        # Send immediate acknowledgment with context awareness
        if context_text:
            thinking = await message.reply_text(
                f'🧠 Understanding: "{text[:50]}{"..." if len(text) > 50 else ""}" (with context)'
            )
        else:
            thinking = await message.reply_text(
                f'🧠 Processing: "{text[:50]}{"..." if len(text) > 50 else ""}"'
            )
        
        # Parse with enhanced AI and conversation context
        if task_parser:
            analysis = await parse_task_with_context(full_message, user_sessions.get(user_id), conversation_context)
        else:
            # Fallback parsing
            analysis = {
                'parsed_task': text,
                'eisenhower': '🧠 Brain Dump',
                'energy': 'Medium',
                'time_estimate': '📝 Short (15-30m)',
                'context': ['Quick Win'],
                'assigned_to': None,
                'due_date': None,
                'adhd_notes': '',
                'record_type': 'Task'
            }
        
        # Save to Notion with enhanced properties
        saved, save_message = await save_to_notion_enhanced(analysis, user_name)
        
        # Format enhanced response
        response = format_task_response(analysis, saved, save_message)
        
        # Store bot response in memory
        if memory:
            await memory.store_message(chat_id, response[:200], "Lyco")  # Store truncated response
        
        # Add quick actions keyboard
        keyboard = []
        
        # If task is complex, offer breakdown
        if analysis['energy'] == 'High':
            keyboard.append([InlineKeyboardButton("🔨 Break it down", callback_data=f"breakdown_{thinking.message_id}")])
        
        # If delegated, offer to notify
        if analysis.get('assigned_to') and analysis['assigned_to'] != 'mene':
            keyboard.append([InlineKeyboardButton(f"📱 Notify {analysis['assigned_to'].title()}", callback_data=f"notify_{analysis['assigned_to']}")])
        
        keyboard.append([InlineKeyboardButton("✅ Mark Complete", callback_data=f"complete_{thinking.message_id}")])
        
        reply_markup = InlineKeyboardMarkup(keyboard) if keyboard else None
        
        # Update message with full response
        await thinking.edit_text(
            response, 
            parse_mode='Markdown',
            reply_markup=reply_markup,
            disable_web_page_preview=True
        )
        
        # Log for monitoring
        logger.info(f"Task from {user_name} ({user_id}): {text[:50]} -> {analysis['eisenhower']}")
        
        # ADHD support: Remind about breaks after 5 tasks
        if user_sessions[user_id]['tasks_today'] % 5 == 0:
            await asyncio.sleep(2)
            await message.reply_text(
                "🧠 **ADHD Break Reminder**\n\n"
                "You've captured 5 tasks! Time for a 5-minute break.\n"
                "Stand up, stretch, or grab some water. 💧",
                parse_mode='Markdown'
            )
        
    except Exception as e:
        logger.error(f"❌ Error in handle_message: {e}")
        await message.reply_text("Sorry, I encountered an error. Please try again.")

async def parse_task_with_context(message: str, user_session: dict, conversation_context: list) -> dict:
    """Enhanced AI task parser with conversation context"""
    
    try:
        # Build context summary for AI
        context_summary = ""
        if conversation_context:
            recent_tasks = []
            for msg in conversation_context:
                if any(word in msg['content'].lower() for word in ['task', 'remind', 'buy', 'call', 'email', 'schedule']):
                    recent_tasks.append(f"- {msg['user']}: {msg['content']}")
            
            if recent_tasks:
                context_summary = f"Recent conversation context:\n" + "\n".join(recent_tasks[-3:]) + "\n\n"
        
        # Enhanced system prompt with context
        system_prompt = f"""You are Lyco, an AI task management assistant for the Demestihas family with ADHD support.

Family Context:
- Mene: Father, physician, ADHD, creates most tasks
- Cindy: Mother, ER physician, ADHD, speaks Spanish  
- Persy: 11yo, 6th grade, loves reading and weather
- Stelios: 8yo, 4th grade, soccer fan (Arsenal)
- Franci: 5yo, kindergarten, loves singing/dancing
- Viola: Au pair from Germany

{context_summary}IMPORTANT: Use conversation context to understand references like "that", "it", "the thing we discussed", "also", "and", etc.

For task creation:
1. Extract clear, actionable tasks
2. Use context to resolve ambiguous references
3. Assign to appropriate family member if mentioned
4. Set reasonable priorities and timeframes
5. Consider ADHD needs (break down complex tasks)

Current user request: {message}

Respond conversationally and extract task details for Notion."""

        # Call task parser with enhanced context
        if task_parser and task_parser.anthropic:
            analysis = await task_parser.parse_with_ai(message, user_session, system_prompt)
        else:
            # Fallback
            analysis = {
                'parsed_task': message,
                'eisenhower': '🧠 Brain Dump',
                'energy': 'Medium',
                'time_estimate': '📝 Short (15-30m)',
                'context': ['Quick Win'],
                'assigned_to': None,
                'due_date': None,
                'adhd_notes': 'Parsed with conversation context',
                'record_type': 'Task'
            }
        
        return analysis
        
    except Exception as e:
        logger.error(f"❌ Context parsing error: {e}")
        return {
            'parsed_task': message,
            'eisenhower': '🧠 Brain Dump',
            'energy': 'Medium',
            'time_estimate': '📝 Short (15-30m)',
            'context': ['Quick Win'],
            'assigned_to': None,
            'due_date': None,
            'adhd_notes': 'Fallback parsing used',
            'record_type': 'Task'
        }

def format_task_response(analysis: dict, saved: bool, save_message: str) -> str:
    """Format the task/shopping analysis response"""
    record_type = analysis.get('record_type', 'Task')
    
    # Task response (simplified for v6)
    response = f'''✅ **Task Captured!**

📝 **Task:** {analysis['parsed_task']}
📊 **Priority:** {analysis['eisenhower']}'''
    
    # Add assignment if delegated
    if analysis.get('assigned_to'):
        family_names = {
            'cindy': 'Cindy (Wife)',
            'viola': 'Viola (Au Pair)',
            'persy': 'Persy (11yo)',
            'stelios': 'Stelios (8yo)', 
            'franci': 'Franci (5yo)',
            'mene': 'You'
        }
        assignee = family_names.get(analysis['assigned_to'], analysis['assigned_to'].title())
        response += f'\n👤 **Assigned:** {assignee}'
    
    response += f'''
⚡ **Energy:** {analysis['energy']}
⏱️ **Time:** {analysis['time_estimate']}
🏷️ **Context:** {', '.join(analysis['context'])}'''
    
    if analysis.get('due_date'):
        response += f"\n📅 **Due:** {analysis['due_date']}"
    
    # Save status
    response += "\n\n"
    if saved:
        response += "✨ **Saved to Notion!**"
    else:
        response += f"⚠️ **Save failed:** {save_message}"
    
    return response

async def save_to_notion_enhanced(task_data: dict, user_name: str) -> tuple[bool, str]:
    """Enhanced Notion save with family fields and shopping support"""
    headers = {
        'Authorization': f'Bearer {NOTION_TOKEN}',
        'Content-Type': 'application/json',
        'Notion-Version': NOTION_VERSION
    }
    
    # Build properties with all fields
    properties = {
        'Name': {
            'title': [{
                'text': {'content': task_data['parsed_task']}
            }]
        },
        'Source': {
            'select': {'name': 'Telegram'}
        },
        'Notes': {
            'rich_text': [{
                'text': {
                    'content': f"Added by {user_name} via Lyco v6 (with memory)\n"
                              f"Time: {datetime.now().strftime('%Y-%m-%d %H:%M')}\n"
                              f"{task_data.get('adhd_notes', '')}"
                }
            }]
        }
    }
    
    # Task-specific fields
    if task_data.get('eisenhower'):
        properties['Eisenhower'] = {
            'select': {'name': task_data['eisenhower']}
        }
    properties['Energy Level Required'] = {
        'select': {'name': task_data['energy']}
    }
    properties['Time Estimate'] = {
        'select': {'name': task_data['time_estimate']}
    }
    
    # Add context tags
    if task_data.get('context'):
        properties['Context/Tags'] = {
            'multi_select': [{'name': tag} for tag in task_data['context']]
        }
    
    # Add due date
    if task_data.get('due_date'):
        properties['Due Date'] = {
            'date': {'start': task_data['due_date']}
        }
    
    # Add family member assignment
    if task_data.get('assigned_to'):
        existing_notes = properties['Notes']['rich_text'][0]['text']['content']
        properties['Notes']['rich_text'][0]['text']['content'] = (
            f"Assigned to: {task_data['assigned_to'].title()}\n{existing_notes}"
        )
    
    # Prepare request
    notion_data = {
        'parent': {'database_id': NOTION_DATABASE_ID},
        'properties': properties
    }
    
    logger.info(f"Saving to Notion: {task_data['parsed_task'][:50]}")
    
    try:
        async with aiohttp.ClientSession() as session:
            async with session.post(
                'https://api.notion.com/v1/pages',
                headers=headers,
                json=notion_data,
                timeout=10
            ) as response:
                if response.status == 200:
                    result = await response.json()
                    return True, f"ID: {result['id'][:8]}"
                else:
                    error_text = await response.text()
                    logger.error(f"Notion error: {error_text}")
                    return False, f"API error {response.status}"
                    
    except asyncio.TimeoutError:
        return False, "Timeout"
    except Exception as e:
        logger.error(f"Notion save error: {e}")
        return False, str(e)[:50]

async def button_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle inline button callbacks"""
    query = update.callback_query
    await query.answer()
    
    data = query.data
    
    if data == 'family_mode':
        await query.edit_message_text(
            "👨‍👩‍👧‍👦 **Family Mode Active!**\n\n"
            "I'll now suggest family member assignments for tasks.\n\n"
            "Try: 'Ask Viola to take kids to soccer' or 'Wife needs to call pediatrician'",
            parse_mode='Markdown'
        )
        
    elif data == 'energy_check':
        keyboard = [
            [InlineKeyboardButton("🔋 High Energy", callback_data='energy_high')],
            [InlineKeyboardButton("⚡ Medium Energy", callback_data='energy_medium')],
            [InlineKeyboardButton("🪫 Low Energy", callback_data='energy_low')]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await query.edit_message_text(
            "⚡ **Energy Check**\n\nHow's your energy level right now?",
            parse_mode='Markdown',
            reply_markup=reply_markup
        )
        
    elif data.startswith('energy_'):
        level = data.split('_')[1]
        suggestions = {
            'high': "🔋 **High Energy!** Perfect for:\n• Deep work tasks\n• Complex projects\n• Important decisions\n• Creative work",
            'medium': "⚡ **Medium Energy!** Good for:\n• Regular tasks\n• Email and calls\n• Planning\n• Household tasks",
            'low': "🪫 **Low Energy** - Take it easy:\n• Quick wins only\n• Simple errands\n• Routine tasks\n• Or just rest!"
        }
        
        await query.edit_message_text(
            suggestions.get(level, "Energy logged!"),
            parse_mode='Markdown'
        )
        
    elif data.startswith('breakdown_'):
        await query.edit_message_text(
            "🔨 **Breaking down task...**\n\n"
            "1. Start with the easiest part\n"
            "2. Set a 15-minute timer\n"
            "3. Do just one small step\n"
            "4. Take a 5-minute break\n"
            "5. Repeat if energy allows",
            parse_mode='Markdown'
        )
        
    elif data.startswith('complete_'):
        await query.edit_message_text(
            "✅ **Task marked complete!**\n\n"
            "Great job! Remember to celebrate small wins! 🎉",
            parse_mode='Markdown'
        )
    
    elif data == 'today_tasks':
        user_id = query.from_user.id
        count = user_sessions.get(user_id, {}).get('tasks_today', 0)
        
        await query.edit_message_text(
            f"📊 **Today's Progress**\n\n"
            f"Tasks captured: {count}\n"
            f"Memory: {'✅ Active' if memory and memory.redis_client else '❌ Disabled'}\n\n"
            f"Remember: Progress > Perfection! 💪",
            parse_mode='Markdown'
        )

async def status(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Enhanced status check with memory status"""
    status_msg = "**🔍 System Status v6**\n\n"
    
    # Bot status
    status_msg += "🟢 **Bot:** Lyco v6 Online\n"
    
    # Memory status
    if memory and memory.redis_client:
        status_msg += "🟢 **Memory:** Redis Connected\n"
    else:
        status_msg += "🔴 **Memory:** Redis Disconnected\n"
    
    # AI status
    if task_parser and task_parser.anthropic:
        status_msg += "🟢 **AI:** Claude Connected\n"
    else:
        status_msg += "🔴 **AI:** No API key\n"
    
    status_msg += "\n**🔧 Configuration**\n"
    status_msg += f"Model: Claude 3 Haiku\n"
    status_msg += f"Memory: 10-message window"
    
    await update.message.reply_text(status_msg, parse_mode='Markdown')

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Help command with memory examples"""
    help_text = '''**📚 Lyco v6 Help Guide**

**Basic Commands:**
/start - Initialize bot (clears memory)
/status - Check system status
/help - This guide

**🧠 Memory Features:**
I remember our last 10 messages, so you can:
• "Also get bread" (refers to previous shopping)
• "Make that urgent" (changes priority)
• "Assign it to Viola" (delegates last task)

**Task Examples:**

**Simple tasks:**
• "Buy milk"
• "Call dentist"
• "Email report to team"

**With context:**
• "Buy milk" → "Also get bread and eggs"
• "Schedule meeting" → "Make it for tomorrow"
• "Create task" → "Assign it to Cindy"

**🧠 ADHD Support:**
• Context awareness reduces cognitive load
• Conversation memory helps track thoughts
• Break down complex requests naturally

**Need more help?** Just ask!'''
    
    await update.message.reply_text(help_text, parse_mode='Markdown')

# Test functions for Redis memory
async def get_context(chat_id: int) -> list:
    """Test function for getting context (for success test)"""
    if memory:
        return await memory.get_context(chat_id)
    return []

async def store_message(chat_id: int, message: str, user: str = "User") -> bool:
    """Test function for storing message (for success test)"""
    if memory:
        return await memory.store_message(chat_id, message, user)
    return False

async def main():
    """Enhanced main function with Redis memory initialization"""
    global memory
    
    if not BOT_TOKEN:
        logger.error('No TELEGRAM_BOT_TOKEN found!')
        print("❌ ERROR: Set TELEGRAM_BOT_TOKEN environment variable")
        return
    
    if not ANTHROPIC_API_KEY:
        logger.warning('No ANTHROPIC_API_KEY - running with limited features')
        print("⚠️  WARNING: Set ANTHROPIC_API_KEY for AI features")
    
    # Initialize Redis memory
    memory = RedisMemory()
    await memory.connect()
    
    logger.info('Starting Lyco bot v6 with memory...')
    print("🚀 Lyco Bot v6 Starting with Redis Memory...")
    print(f"✅ Notion Database: {NOTION_DATABASE_ID}")
    print(f"✅ AI Parser: {'Enabled' if task_parser else 'Disabled'}")
    print(f"✅ Memory: {'Connected' if memory.redis_client else 'Failed'}")
    
    # Create application
    application = Application.builder().token(BOT_TOKEN).build()
    
    # Command handlers
    application.add_handler(CommandHandler('start', start))
    application.add_handler(CommandHandler('status', status))
    application.add_handler(CommandHandler('help', help_command))
    
    # Message handler for tasks
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    
    # Button callback handler
    application.add_handler(CallbackQueryHandler(button_callback))
    
    # Start bot
    print("✅ Bot ready! Waiting for messages...")
    logger.info('Bot v6 started successfully with memory support')
    
    try:
        await application.run_polling(allowed_updates=Update.ALL_TYPES)
    finally:
        # Cleanup
        if memory:
            await memory.disconnect()

if __name__ == '__main__':
    asyncio.run(main())
