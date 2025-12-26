#!/bin/bash
# Run script for MiMerc Telegram Bot

echo "================================"
echo "MiMerc Telegram Bot Launcher"
echo "================================"

# Check if .env file exists
if [ ! -f .env ]; then
    echo "❌ Error: .env file not found!"
    echo "Please copy .env.example to .env and add your credentials:"
    echo "  cp .env.example .env"
    exit 1
fi

# Check for Python 3
if ! command -v python3 &> /dev/null; then
    echo "❌ Error: Python 3 is not installed!"
    exit 1
fi

echo "✅ Environment file found"
echo "✅ Python 3 detected"

# Install dependencies if needed
echo ""
echo "Checking dependencies..."
pip3 install -q python-telegram-bot python-dotenv 2>/dev/null || {
    echo "Installing dependencies..."
    pip3 install -r requirements.txt
}

echo ""
echo "Starting MiMerc Telegram Bot..."
echo "Press Ctrl+C to stop"
echo "================================"

# Run the bot
python3 telegram_bot.py
