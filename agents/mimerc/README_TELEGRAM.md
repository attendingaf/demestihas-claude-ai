# MiMerc Telegram Bot

A production-ready Telegram bot interface for the MiMerc grocery list management agent.

## Features

### Core Functionality
- ✅ Natural language processing for grocery list management
- 📝 Command-based interactions (/add, /remove, /list, /clear)
- 👨‍👩‍👧‍👦 Family/group chat support with shared lists
- 💾 Persistent state via PostgreSQL
- 🎛️ Custom keyboards and inline buttons for better UX
- 🔄 Thread-based isolation for multi-user support

### Commands
- `/start` - Welcome message with instructions
- `/list` - Show current grocery list
- `/add [items]` - Quick add items (e.g., `/add milk eggs`)
- `/remove [items]` - Remove items from list
- `/clear` - Clear list with confirmation dialog
- `/help` - Show all available commands

### Natural Language Examples
The bot understands natural language requests:
- "Add milk and bread to the list"
- "Remove eggs"
- "What's on my list?"
- "Add 2 pounds of chicken"
- "Show me my grocery list"

## Setup Instructions

### 1. Get a Telegram Bot Token

1. Open Telegram and search for `@BotFather`
2. Send `/newbot` command
3. Choose a name for your bot (e.g., "MiMerc Grocery Bot")
4. Choose a username (must end with 'bot', e.g., `mimerc_grocery_bot`)
5. Copy the token provided by BotFather

### 2. Configure Environment

Copy the example environment file:
```bash
cp .env.example .env
```

Edit `.env` and add your credentials:
```bash
TELEGRAM_BOT_TOKEN=your_bot_token_here
OPENAI_API_KEY=your_openai_api_key
PG_CONNINFO=postgresql://user:pass@localhost:5432/mimerc_db
```

### 3. Install Dependencies

```bash
pip install -r requirements.txt
```

### 4. Run the Bot

#### Local Development
```bash
python telegram_bot.py
```

#### Docker Deployment
Add to `docker-compose.yml`:
```yaml
telegram-bot:
  build: .
  container_name: mimerc-telegram
  depends_on:
    mimerc-db:
      condition: service_healthy
  environment:
    - TELEGRAM_BOT_TOKEN=${TELEGRAM_BOT_TOKEN}
    - OPENAI_API_KEY=${OPENAI_API_KEY}
    - PG_CONNINFO=postgresql://${POSTGRES_USER}:${POSTGRES_PASSWORD}@mimerc-db:5432/${POSTGRES_DB}
  command: python telegram_bot.py
  restart: unless-stopped
```

## Usage Examples

### Personal Chat
```
User: /start
Bot: 👋 Welcome! I'm MiMerc, your smart grocery assistant.
     [Shows custom keyboard with quick actions]

User: Add milk, eggs, and bread
Bot: ✅ Added milk, eggs, and bread to your list

User: What's on my list?
Bot: 📋 Your Grocery List:
     • milk
     • eggs
     • bread
     [Shows action buttons]

User: /clear
Bot: ⚠️ Are you sure you want to clear your entire grocery list?
     [Yes] [No]
```

### Group Chat
When added to a group chat, the bot automatically shares the list among all members:

```
Mom: Add chicken and vegetables
Bot: ✅ Added chicken and vegetables to the list

Dad: /list
Bot: 📋 Your Grocery List:
     • chicken
     • vegetables

Kid: Add ice cream please!
Bot: ✅ Added ice cream to the list
```

## Thread Management

The bot uses thread IDs to maintain separate lists:
- **Personal lists**: `telegram_{user_id}`
- **Group lists**: `group_{chat_id}`
- **Family mode**: `family_{group_id}`

## Custom Keyboards

The bot includes custom keyboards for quick actions:
- 📝 View List
- ➕ Quick Add
- 🗑️ Clear List
- 👨‍👩‍👧‍👦 Family Mode / 👤 Personal Mode
- ❓ Help

## Production Deployment

### Systemd Service

Create `/etc/systemd/system/mimerc-telegram.service`:

```ini
[Unit]
Description=MiMerc Telegram Bot
After=network.target postgresql.service

[Service]
Type=simple
User=mimerc
WorkingDirectory=/opt/mimerc
Environment="PATH=/usr/bin:/usr/local/bin"
ExecStart=/usr/bin/python3 /opt/mimerc/telegram_bot.py
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
```

Enable and start:
```bash
sudo systemctl enable mimerc-telegram
sudo systemctl start mimerc-telegram
```

## Testing Checklist

### Basic Operations
- [x] `/start` shows welcome message with instructions
- [x] Can add items via command: `/add milk`
- [x] Can add items naturally: "Please add eggs to my list"
- [x] `/list` shows current items
- [x] Items persist between bot restarts
- [x] `/clear` asks for confirmation before clearing

### Thread Isolation
- [x] Different users have separate lists
- [x] Group chats share lists among members
- [x] Family mode switches between personal/shared lists

### Error Handling
- [x] Bot handles malformed input gracefully
- [x] Database disconnections are handled
- [x] Friendly error messages shown to users

## Advanced Features (Future)

### Voice Message Support
Currently shows acknowledgment. Future implementation will use Whisper API for transcription.

### Shopping Reminders
Planned feature to send reminders based on shopping patterns.

### Recipe Integration
Future feature to add ingredients from recipes directly to the list.

## Troubleshooting

### Bot not responding
1. Check bot token is correct
2. Verify database connection
3. Check logs: `docker-compose logs telegram-bot`

### Database connection issues
1. Ensure PostgreSQL is running
2. Verify PG_CONNINFO is correct
3. Check network connectivity between bot and database

### Group chat issues
1. Ensure bot has proper permissions in group
2. Bot must be admin for some features
3. Check privacy mode settings in BotFather

## Security Notes

- Never commit `.env` file with real tokens
- Use environment variables for all secrets
- Rotate bot token if compromised
- Use HTTPS webhooks in production (instead of polling)

## Support

For issues or questions:
1. Check logs for error messages
2. Verify all environment variables are set
3. Ensure database tables are created (run agent.py first)
4. Test with simple commands before complex natural language