# MiMerc Telegram Bot Setup

## 🚀 Quick Start (5 minutes)

### 1. Create Your Bot
1. Open Telegram and search for **@BotFather**
2. Send `/newbot` 
3. Choose a name: "MiMerc Grocery Bot"
4. Choose a username: `YourNameMiMercBot` (must end in 'bot')
5. Save the token you receive (looks like: `6234567890:ABCdefGHIjklMNOpqrsTUVwxyz`)

### 2. Configure Environment
```bash
cd /Users/menedemestihas/Projects/demestihas-ai/agents/mimerc

# Add to .env file
echo "TELEGRAM_BOT_TOKEN=YOUR_TOKEN_HERE" >> .env
```

### 3. Install Dependencies
```bash
# Add telegram dependencies to requirements.txt
pip install python-telegram-bot==20.7
pip install python-dotenv
```

### 4. Test Locally
```bash
# Run the bot
python telegram_bot.py

# You should see:
# "Starting MiMerc Telegram bot..."
# "MiMerc agent initialized successfully"
```

### 5. Test in Telegram
1. Open Telegram
2. Search for your bot username
3. Send `/start`
4. Try: "Add milk and eggs to my list"

## 📱 Bot Features

### Commands
- `/start` - Welcome message with custom keyboard
- `/list` - View current grocery list
- `/add [items]` - Quick add items
- `/remove [items]` - Remove specific items
- `/clear` - Clear entire list (with confirmation)
- `/family` - Switch to family shared list
- `/help` - Show all commands

### Natural Language
Just type normally:
- "Add 2 pounds of chicken"
- "We need milk, eggs, and bread"
- "Remove the eggs"
- "What's on my list?"

### Custom Keyboard
Quick access buttons:
- 📝 View List
- ➕ Quick Add
- 🗑️ Clear List
- 👨‍👩‍👧‍👦 Family Mode
- 📊 List Stats
- ⚙️ Settings

### Group Chat Support
Add bot to family group:
1. Add bot to group
2. Make bot admin (optional, for better features)
3. Everyone can add/view shared list
4. Messages show who added what

## 🐳 Production Deployment

### Option A: Docker Deployment
```dockerfile
# Dockerfile.telegram
FROM python:3.11-slim

WORKDIR /app

# Install dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy bot files
COPY agent.py telegram_bot.py ./
COPY .env ./

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
  CMD python -c "import requests; requests.get('https://api.telegram.org/bot${TELEGRAM_BOT_TOKEN}/getMe')"

# Run bot
CMD ["python", "telegram_bot.py"]
```

### Option B: Systemd Service (VM)
```ini
# /etc/systemd/system/mimerc-telegram.service
[Unit]
Description=MiMerc Telegram Bot
After=network.target postgresql.service

[Service]
Type=simple
User=mimerc
WorkingDirectory=/home/mimerc/mimerc-bot
Environment="PATH=/home/mimerc/mimerc-bot/venv/bin"
ExecStart=/home/mimerc/mimerc-bot/venv/bin/python telegram_bot.py
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
```

### Option C: Docker Compose Integration
```yaml
# Add to docker-compose.yml
mimerc-telegram:
  build:
    context: .
    dockerfile: Dockerfile.telegram
  container_name: mimerc-telegram
  depends_on:
    mimerc-db:
      condition: service_healthy
  environment:
    TELEGRAM_BOT_TOKEN: ${TELEGRAM_BOT_TOKEN}
    PG_CONNINFO: "postgresql://mimerc:${POSTGRES_PASSWORD}@mimerc-db:5432/mimerc_db"
  restart: unless-stopped
  networks:
    - mimerc-network
```

## 🔧 Advanced Configuration

### Set Bot Commands (in BotFather)
Send to @BotFather:
```
/setcommands

list - View grocery list
add - Add items to list
remove - Remove items
clear - Clear entire list
family - Switch to family list
help - Show help message
```

### Set Bot Description
```
/setdescription

🛒 MiMerc - Your AI Grocery Assistant

Manage shopping lists with natural language. Works for personal or family lists. Just tell me what you need!

Features:
• Natural language understanding
• Family shared lists  
• Voice message support
• Group chat compatible
```

### Enable Inline Mode (Optional)
```
/setinline

Users can type @YourBot milk to quickly check if milk is on the list
```

## 🔒 Security Best Practices

### 1. Environment Variables
Never commit tokens:
```bash
# .gitignore
.env
*.token
config.json
```

### 2. Rate Limiting
Bot includes built-in flood protection via python-telegram-bot

### 3. User Validation  
```python
# Add to bot for private deployment
ALLOWED_USERS = [123456789, 987654321]  # Your Telegram IDs

async def validate_user(update: Update) -> bool:
    return update.effective_user.id in ALLOWED_USERS
```

### 4. Database Security
- Use connection pooling (already implemented)
- Prepared statements prevent SQL injection
- Thread IDs isolate user data

## 🧪 Testing Checklist

- [ ] Bot responds to /start
- [ ] Can add items with natural language
- [ ] List persists between restarts
- [ ] Family mode switches correctly
- [ ] Works in group chats
- [ ] Confirmation for clear command
- [ ] Error messages are friendly
- [ ] Database persists data

## 📊 Monitoring

### Basic Health Check
```python
# Add to bot for monitoring
@bot.command("health")
async def health_check(update, context):
    try:
        # Check database
        test = await process_message("test", "health_check")
        await update.message.reply_text("✅ All systems operational")
    except:
        await update.message.reply_text("⚠️ Database issue detected")
```

### Logging
Bot logs to console by default. For production:
```python
# Add file logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO,
    handlers=[
        logging.FileHandler('/var/log/mimerc-telegram.log'),
        logging.StreamHandler()
    ]
)
```

## 🎯 Next Features to Add

### Phase 1 (Easy)
- [ ] Voice transcription with Whisper
- [ ] Shopping mode (check off items)
- [ ] List statistics
- [ ] Export list as text

### Phase 2 (Medium)  
- [ ] Receipt OCR with Tesseract
- [ ] Recipe integration
- [ ] Budget tracking
- [ ] Store preferences

### Phase 3 (Advanced)
- [ ] Meal planning
- [ ] Nutrition tracking
- [ ] Price comparison
- [ ] Expiry reminders

## 🆘 Troubleshooting

### Bot not responding
```bash
# Check token is set
echo $TELEGRAM_BOT_TOKEN

# Test token manually  
curl https://api.telegram.org/bot$TELEGRAM_BOT_TOKEN/getMe

# Check logs
python telegram_bot.py
# Look for initialization errors
```

### Database connection issues
```bash
# Test database connection
psql $PG_CONNINFO -c "SELECT 1"

# Check if tables exist
psql $PG_CONNINFO -c "\dt"
```

### Bot offline after restart
```bash
# Enable systemd service
sudo systemctl enable mimerc-telegram
sudo systemctl start mimerc-telegram
sudo systemctl status mimerc-telegram
```

## 📱 Share with Family

1. Send them the bot link: `https://t.me/YourBotUsername`
2. Have them send `/start`
3. For shared lists:
   - Create family group chat
   - Add bot to group
   - Everyone uses the same list!

---

## Ready to Deploy!

Your Telegram bot is ready. Just:
1. Set your token in .env
2. Run `python telegram_bot.py`
3. Message your bot on Telegram

The bot will handle the rest! 🚀
