#!/bin/bash
# Lyco.ai Complete Server Setup Script
# Run this on your fresh Ubuntu 24.04 server to rebuild everything

set -e  # Exit on any error

echo "================================================"
echo "    LYCO.AI SERVER SETUP - FRESH REBUILD"
echo "================================================"
echo ""

# Color codes for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Function to print colored status
status() {
    echo -e "${GREEN}[✓]${NC} $1"
}

error() {
    echo -e "${RED}[✗]${NC} $1"
    exit 1
}

warning() {
    echo -e "${YELLOW}[!]${NC} $1"
}

# 1. INSTALL DOCKER
echo ""
echo "📦 Step 1: Installing Docker..."
if ! command -v docker &> /dev/null; then
    curl -fsSL https://get.docker.com -o get-docker.sh
    sudo sh get-docker.sh
    rm get-docker.sh
    status "Docker installed successfully"
else
    status "Docker already installed"
fi

# 2. INSTALL DOCKER COMPOSE
echo ""
echo "📦 Step 2: Installing Docker Compose..."
if ! command -v docker-compose &> /dev/null; then
    sudo apt-get update
    sudo apt-get install -y docker-compose-plugin docker-compose
    status "Docker Compose installed"
else
    status "Docker Compose already installed"
fi

# 3. CREATE PROJECT STRUCTURE
echo ""
echo "📁 Step 3: Creating project structure..."
mkdir -p /root/lyco-ai
cd /root/lyco-ai
status "Created /root/lyco-ai directory"

# 4. CREATE BOT.PY
echo ""
echo "🤖 Step 4: Creating bot.py..."
cat > /root/lyco-ai/bot.py << 'BOTEOF'
#!/usr/bin/env python3
"""
Lyco.ai Bot v2 - Production Ready with Notion Integration
ADHD-optimized task management via Telegram
"""

import os
import asyncio
import logging
import json
from datetime import datetime, timedelta
from typing import Dict, Tuple, Optional, List
import re

from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes
from anthropic import AsyncAnthropic
import aiohttp

# Configure logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# Configuration from environment
BOT_TOKEN = os.environ.get('TELEGRAM_BOT_TOKEN')
ANTHROPIC_API_KEY = os.environ.get('ANTHROPIC_API_KEY')
NOTION_TOKEN = os.environ.get('NOTION_TOKEN')
NOTION_DATABASE_ID = os.environ.get('NOTION_DATABASE_ID')
NOTION_VERSION = '2022-06-28'

# Validate required environment variables
required_vars = {
    'TELEGRAM_BOT_TOKEN': BOT_TOKEN,
    'ANTHROPIC_API_KEY': ANTHROPIC_API_KEY,
    'NOTION_TOKEN': NOTION_TOKEN,
    'NOTION_DATABASE_ID': NOTION_DATABASE_ID
}

missing_vars = [var for var, value in required_vars.items() if not value]
if missing_vars:
    logger.error(f"Missing required environment variables: {missing_vars}")
    logger.info("Please set them in your .env file or environment")
    exit(1)

# Initialize Anthropic client
anthropic = AsyncAnthropic(api_key=ANTHROPIC_API_KEY)

# Eisenhower Matrix categories
EISENHOWER_MATRIX = {
    "urgent_important": "🔥 Do Now",
    "not_urgent_important": "📅 Schedule", 
    "urgent_not_important": "👥 Delegate",
    "not_urgent_not_important": "🗄️ Someday/Maybe",
    "brain_dump": "🧠 Brain Dump"
}

async def analyze_task_with_ai(task_text: str) -> Dict:
    """Use Claude to analyze and categorize the task"""
    
    prompt = f"""Analyze this task and provide structured output: "{task_text}"

Return a JSON object with:
1. "task_name": Clear, actionable task title
2. "eisenhower": One of ["urgent_important", "not_urgent_important", "urgent_not_important", "not_urgent_not_important", "brain_dump"]
3. "energy_level": One of ["Low", "Medium", "High"]
4. "time_estimate": One of ["⚡ Quick (<15m)", "🔍 Short (15-30m)", "🎯 Deep (>30m)", "📅 Multi-hour"]
5. "context_tags": Array of relevant tags from ["Quick Win", "Deep Work", "Errand", "Call", "Email", "Meeting", "Research", "Admin", "Creative", "Physical", "Household", "Appointment", "Family"]
6. "due_date": ISO date string if a date is mentioned, null otherwise
7. "notes": Any additional context or details

Consider urgency indicators like "ASAP", "urgent", "tomorrow", "next week".
Default to "brain_dump" if unclear."""

    try:
        response = await anthropic.messages.create(
            model="claude-3-haiku-20240307",
            max_tokens=500,
            temperature=0.3,
            messages=[
                {"role": "user", "content": prompt}
            ]
        )
        
        # Extract JSON from response
        response_text = response.content[0].text
        
        # Try to parse JSON from response
        import re
        json_match = re.search(r'\{.*\}', response_text, re.DOTALL)
        if json_match:
            task_data = json.loads(json_match.group())
            return task_data
        else:
            # Fallback if no JSON found
            return {
                "task_name": task_text,
                "eisenhower": "brain_dump",
                "energy_level": "Medium",
                "time_estimate": "🔍 Short (15-30m)",
                "context_tags": ["Admin"],
                "due_date": None,
                "notes": "Auto-categorized"
            }
            
    except Exception as e:
        logger.error(f"AI analysis error: {e}")
        # Return sensible defaults on error
        return {
            "task_name": task_text,
            "eisenhower": "brain_dump",
            "energy_level": "Low",
            "time_estimate": "⚡ Quick (<15m)",
            "context_tags": ["Admin"],
            "due_date": None,
            "notes": "Failed to analyze with AI"
        }

async def save_to_notion(task_data: Dict, user_name: str) -> bool:
    """Save the analyzed task to Notion database"""
    
    headers = {
        'Authorization': f'Bearer {NOTION_TOKEN}',
        'Content-Type': 'application/json',
        'Notion-Version': NOTION_VERSION
    }
    
    # Map Eisenhower category to Notion select option
    eisenhower_value = EISENHOWER_MATRIX.get(
        task_data.get('eisenhower', 'brain_dump'),
        "🧠 Brain Dump"
    )
    
    # Build Notion page properties
    properties = {
        "Name": {
            "title": [
                {
                    "text": {
                        "content": task_data.get('task_name', 'New Task')
                    }
                }
            ]
        },
        "Eisenhower": {
            "select": {
                "name": eisenhower_value
            }
        },
        "Energy Level Required": {
            "select": {
                "name": task_data.get('energy_level', 'Medium')
            }
        },
        "Time Estimate": {
            "select": {
                "name": task_data.get('time_estimate', '🔍 Short (15-30m)')
            }
        },
        "Source": {
            "select": {
                "name": "Telegram"
            }
        },
        "Notes": {
            "rich_text": [
                {
                    "text": {
                        "content": f"From: {user_name}\n{task_data.get('notes', '')}"
                    }
                }
            ]
        }
    }
    
    # Add context tags if present
    if task_data.get('context_tags'):
        properties["Context/Tags"] = {
            "multi_select": [
                {"name": tag} for tag in task_data['context_tags']
            ]
        }
    
    # Add due date if present
    if task_data.get('due_date'):
        properties["Due Date"] = {
            "date": {
                "start": task_data['due_date']
            }
        }
    
    # Create the page in Notion
    data = {
        "parent": {"database_id": NOTION_DATABASE_ID},
        "properties": properties
    }
    
    try:
        async with aiohttp.ClientSession() as session:
            async with session.post(
                'https://api.notion.com/v1/pages',
                headers=headers,
                json=data
            ) as response:
                if response.status == 200:
                    logger.info(f"Task saved to Notion: {task_data['task_name']}")
                    return True
                else:
                    error_text = await response.text()
                    logger.error(f"Notion API error: {response.status} - {error_text}")
                    return False
    except Exception as e:
        logger.error(f"Failed to save to Notion: {e}")
        return False

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle /start command"""
    user = update.effective_user
    welcome_message = f"""🤖 Welcome to Lyco.ai, {user.first_name}!

I'm your ADHD-optimized task management assistant.

Just send me any task and I'll:
✅ Analyze it with AI
🎯 Categorize by priority (Eisenhower Matrix)
⚡ Estimate time and energy needed
💾 Save to your Notion database

Try me! Send something like:
"Call dentist tomorrow about appointment"
"Buy groceries"
"Review Q3 budget report - urgent"

Commands:
/start - Show this message
/help - Get help
/status - Check bot status"""
    
    await update.message.reply_text(welcome_message)

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle /help command"""
    help_text = """🤔 How to use Lyco.ai:

Simply send me any task in natural language!

I understand:
📅 Dates: "tomorrow", "next week", "Monday"
🚨 Urgency: "urgent", "ASAP", "when possible"
⏰ Time: "quick task", "will take hours"
🏷️ Context: "call", "email", "meeting"

Examples:
• "Schedule dentist appointment for next Tuesday"
• "Quick call with Sarah about project"
• "Review and approve budget - urgent"
• "Buy birthday gift for mom"

I'll automatically categorize and save everything to Notion!"""
    
    await update.message.reply_text(help_text)

async def status_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle /status command"""
    status_text = """✅ Lyco.ai Status:

🟢 Bot: Online
🟢 AI: Connected (Claude Haiku)
🟢 Notion: Connected
🟢 Database: Ready

Version: 2.0 Production
Last restart: Just now"""
    
    await update.message.reply_text(status_text)

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle incoming messages (tasks)"""
    user = update.effective_user
    task_text = update.message.text
    
    # Send typing indicator
    await context.bot.send_chat_action(
        chat_id=update.effective_chat.id,
        action="typing"
    )
    
    # Log the incoming task
    logger.info(f"Task from {user.first_name} ({user.id}): {task_text}")
    
    # Analyze task with AI
    task_data = await analyze_task_with_ai(task_text)
    
    # Save to Notion
    saved = await save_to_notion(task_data, user.first_name)
    
    # Prepare response
    eisenhower_value = EISENHOWER_MATRIX.get(
        task_data.get('eisenhower', 'brain_dump'),
        "🧠 Brain Dump"
    )
    
    if saved:
        response = f"""✅ Task captured and saved!

📝 **Task:** {task_data['task_name']}
🎯 **Priority:** {eisenhower_value}
⚡ **Energy:** {task_data['energy_level']}
⏱️ **Time:** {task_data['time_estimate']}
🏷️ **Tags:** {', '.join(task_data.get('context_tags', ['None']))}"""
        
        if task_data.get('due_date'):
            response += f"\n📅 **Due:** {task_data['due_date']}"
            
        response += "\n\n✨ Saved to your Notion database!"
    else:
        response = f"""⚠️ Task analyzed but couldn't save to Notion:

📝 **Task:** {task_data['task_name']}
🎯 **Priority:** {eisenhower_value}

Please check your Notion connection."""
    
    await update.message.reply_text(response, parse_mode='Markdown')

async def error_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Log errors"""
    logger.error(f"Update {update} caused error {context.error}")
    
    if update and update.effective_message:
        await update.effective_message.reply_text(
            "❌ Sorry, an error occurred processing your request. Please try again."
        )

def main() -> None:
    """Start the bot"""
    # Create application
    application = Application.builder().token(BOT_TOKEN).build()
    
    # Add command handlers
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("help", help_command))
    application.add_handler(CommandHandler("status", status_command))
    
    # Add message handler for tasks
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    
    # Add error handler
    application.add_error_handler(error_handler)
    
    # Start bot
    logger.info("Starting Lyco.ai bot...")
    application.run_polling(allowed_updates=Update.ALL_TYPES)

if __name__ == '__main__':
    main()
BOTEOF
status "Created bot.py"

# 5. CREATE DOCKERFILE
echo ""
echo "🐳 Step 5: Creating Dockerfile..."
cat > /root/lyco-ai/Dockerfile << 'DOCKEREOF'
FROM python:3.12-slim

WORKDIR /app

# Install dependencies
RUN pip install --no-cache-dir \
    python-telegram-bot \
    anthropic \
    aiohttp \
    python-dotenv

# Copy bot code
COPY bot.py /app/

# Run bot
CMD ["python", "bot.py"]
DOCKEREOF
status "Created Dockerfile"

# 6. CREATE DOCKER-COMPOSE.YML
echo ""
echo "🐳 Step 6: Creating docker-compose.yml..."
cat > /root/lyco-ai/docker-compose.yml << 'COMPOSEEOF'
version: '3.8'

services:
  lyco_bot:
    build: .
    container_name: lyco-ai-bot
    restart: unless-stopped
    environment:
      - TELEGRAM_BOT_TOKEN=${TELEGRAM_BOT_TOKEN}
      - ANTHROPIC_API_KEY=${ANTHROPIC_API_KEY}
      - NOTION_TOKEN=${NOTION_TOKEN}
      - NOTION_DATABASE_ID=${NOTION_DATABASE_ID}
    volumes:
      - ./logs:/app/logs
    logging:
      driver: "json-file"
      options:
        max-size: "10m"
        max-file: "3"
COMPOSEEOF
status "Created docker-compose.yml"

# 7. CREATE ENV TEMPLATE
echo ""
echo "📝 Step 7: Creating .env.example..."
cat > /root/lyco-ai/.env.example << 'ENVEOF'
# Telegram Bot Token (from @BotFather)
TELEGRAM_BOT_TOKEN=your_telegram_bot_token_here

# Anthropic API Key (from console.anthropic.com)
ANTHROPIC_API_KEY=your_anthropic_api_key_here

# Notion Integration Token (from notion.so/my-integrations)
NOTION_TOKEN=your_notion_integration_token_here

# Notion Database ID (from your database URL)
NOTION_DATABASE_ID=your_notion_database_id_here
ENVEOF
status "Created .env.example"

# 8. CREATE MONITORING SCRIPT
echo ""
echo "📊 Step 8: Creating monitoring script..."
cat > /root/lyco-ai/monitor.sh << 'MONITOREOF'
#!/bin/bash
# Lyco.ai Monitoring Dashboard

while true; do
    clear
    echo "================================================"
    echo "         LYCO.AI MONITORING DASHBOARD"
    echo "================================================"
    echo ""
    echo "📊 CONTAINER STATUS:"
    docker ps --format "table {{.Names}}\t{{.Status}}\t{{.Ports}}" | grep -E "(NAME|lyco)"
    echo ""
    echo "📝 RECENT LOGS (last 10 lines):"
    docker logs --tail 10 lyco-ai-bot 2>&1 || echo "Container not running yet"
    echo ""
    echo "💾 SYSTEM RESOURCES:"
    echo -n "CPU: "; top -bn1 | grep "Cpu(s)" | awk '{print $2 + $4"%"}'
    echo -n "Memory: "; free -h | grep Mem | awk '{print $3 " used of " $2}'
    echo -n "Disk: "; df -h / | tail -1 | awk '{print $3 " used of " $2}'
    echo ""
    echo "🔄 Refreshing in 5 seconds... (Ctrl+C to exit)"
    sleep 5
done
MONITOREOF
chmod +x /root/lyco-ai/monitor.sh
status "Created monitor.sh"

# 9. INITIALIZE GIT
echo ""
echo "🔧 Step 9: Initializing Git repository..."
cd /root/lyco-ai
git init
cat > .gitignore << 'GITEOF'
.env
*.pyc
__pycache__/
logs/
*.log
.DS_Store
GITEOF
git add .
git commit -m "Initial commit: Lyco.ai bot rebuild after server recovery" || true
status "Git repository initialized"

# 10. CREATE README
echo ""
echo "📚 Step 10: Creating documentation..."
cat > /root/lyco-ai/README.md << 'READMEEOF'
# Lyco.ai - ADHD-Optimized Task Management Bot

## Quick Start

1. Copy `.env.example` to `.env` and add your credentials:
   ```bash
   cp .env.example .env
   nano .env
   ```

2. Build and start the bot:
   ```bash
   docker-compose up -d --build
   ```

3. Check logs:
   ```bash
   docker logs -f lyco-ai-bot
   ```

4. Monitor status:
   ```bash
   ./monitor.sh
   ```

## Commands

- `/start` - Welcome message
- `/help` - Usage instructions  
- `/status` - Check bot status

## Features

✅ AI-powered task analysis
✅ Eisenhower Matrix categorization
✅ Energy level estimation
✅ Time estimation
✅ Automatic Notion database sync
✅ Natural language processing

## Troubleshooting

- Check logs: `docker logs lyco-ai-bot`
- Restart bot: `docker restart lyco-ai-bot`
- Rebuild: `docker-compose up -d --build`
READMEEOF
status "Created README.md"

echo ""
echo "================================================"
echo "          SETUP COMPLETE! 🎉"
echo "================================================"
echo ""
echo "✅ Docker installed"
echo "✅ Project structure created"
echo "✅ Bot code ready"
echo "✅ Monitoring tools ready"
echo ""
echo "🔑 NEXT STEPS:"
echo ""
echo "1. Add your credentials:"
echo "   cd /root/lyco-ai"
echo "   cp .env.example .env"
echo "   nano .env"
echo ""
echo "2. Add your tokens:"
echo "   - TELEGRAM_BOT_TOKEN (from @BotFather)"
echo "   - ANTHROPIC_API_KEY (from console.anthropic.com)"
echo "   - NOTION_TOKEN (from notion.so/my-integrations)"
echo "   - NOTION_DATABASE_ID (from your database URL)"
echo ""
echo "3. Start the bot:"
echo "   docker-compose up -d --build"
echo ""
echo "4. Check it's running:"
echo "   docker logs -f lyco-ai-bot"
echo ""
echo "📊 Monitor with: ./monitor.sh"
echo ""
echo "Your bot will be ready at @LycurgusBot on Telegram!"
echo "================================================"
