# MiMerc Telegram Bot - System State

## Current Working Capabilities

### ⚠️ CRITICAL STATUS
**Persistence fix applied, library compatibility issue**
- Files have been patched ✅
- Database is running ✅
- Telegram library version issue 🔧
- **ACTION REQUIRED**: Run `./fix_and_run.sh`

### Core Agent (agent.py)
✅ **Grocery List Management**
- Add items with quantities
- Remove items (case-insensitive)  
- View current list
- Dictionary-based state tracking

✅ **State Persistence**
- PostgreSQL checkpointer via LangGraph
- Thread-based conversation continuity
- Survives restarts via database

### Telegram Bot (telegram_bot.py)
✅ **Conversational Interface**
- Natural language processing
- No complex commands needed
- Emoji-enhanced responses

✅ **Thread Management**  
- Chat-specific state isolation
- Persistent grocery lists per conversation
- Handles multiple users simultaneously

## Testing Commands

### Test Bot Functionality
```bash
# Start the bot
./run_telegram_bot.sh

# Or directly
python telegram_bot.py
```

### Test State Persistence
```bash
# Run persistence tests
python test_persistence_fix.py

# Check database state
docker exec -it mimerc-postgres psql -U mimerc -d mimerc -c "SELECT * FROM checkpoints;"
```

## Docker Services
- **mimerc-postgres**: PostgreSQL database for state persistence
- **mimerc-bot**: Telegram bot container (if dockerized)

## Environment Variables Required
- `TELEGRAM_BOT_TOKEN`: Bot token from @BotFather
- `OPENAI_API_KEY`: OpenAI API key for LLM
- `PG_CONNINFO`: PostgreSQL connection string

## Known Issues (Pre-Patch)
⚠️ **Critical Bug**: State was being overwritten on each message
- telegram_bot.py was initializing empty grocery_list
- This prevented state persistence across messages
- Fixed in current patch

## Architecture Notes
- LangGraph handles state management
- PostgreSQL stores conversation checkpoints
- Each Telegram chat has unique thread_id
- Synchronous agent wrapped for async Telegram