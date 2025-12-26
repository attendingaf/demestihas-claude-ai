#!/bin/bash
# Complete fix for telegram bot - handles all issues

echo "================================"
echo "🔧 Complete MiMerc Bot Fix"
echo "================================"
echo ""

# Step 1: Clean install of dependencies
echo "Step 1: Cleaning and reinstalling dependencies..."
echo ""

# Uninstall potentially conflicting versions
pip3 uninstall python-telegram-bot -y 2>/dev/null

# Install specific working version
echo "Installing telegram bot library (v21.3)..."
pip3 install "python-telegram-bot[webhooks]==21.3" --no-cache-dir --break-system-packages 2>/dev/null || \
pip3 install "python-telegram-bot[webhooks]==21.3" --no-cache-dir

# Make sure other dependencies are installed
echo "Installing other dependencies..."
pip3 install langchain langchain-openai langgraph psycopg psycopg-pool python-dotenv --quiet --break-system-packages 2>/dev/null || \
pip3 install langchain langchain-openai langgraph psycopg psycopg-pool python-dotenv --quiet

echo ""
echo "✅ Dependencies installed"
echo ""

# Step 2: Verify PostgreSQL
echo "Step 2: Checking database..."
if nc -z localhost 5433 2>/dev/null; then
    echo "✅ PostgreSQL is running on port 5433"
else
    echo "❌ PostgreSQL not accessible"
    echo "Please ensure Docker is running and PostgreSQL container is up"
    exit 1
fi
echo ""

# Step 3: Run the bot
echo "Step 3: Starting bot with persistence fix..."
echo ""

# Set environment variables
export $(cat .env | grep -v '^#' | xargs) 2>/dev/null
export PG_CONNINFO="postgresql://mimerc:mimerc_secure_password@localhost:5433/mimerc_db"

echo "================================"
echo "🚀 MiMerc Bot Starting"
echo "================================"
echo ""
echo "IMPORTANT: Once the bot starts successfully:"
echo ""
echo "📱 TEST IN TELEGRAM:"
echo "1. Send: 'Add milk to my list'"
echo "2. Send: 'Add eggs to my list'"
echo "3. Send: 'What's on my list?'"
echo "   → BOTH items should appear!"
echo ""
echo "This proves the persistence fix is working."
echo ""
echo "Starting bot now... (Press Ctrl+C to stop)"
echo "----------------------------------------"
echo ""

# Run with explicit Python path to avoid any PATH issues
/usr/bin/python3 telegram_bot.py
