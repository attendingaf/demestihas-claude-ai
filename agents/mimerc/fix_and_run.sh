#!/bin/bash
# Fix telegram bot library compatibility issue

echo "================================"
echo "🔧 Fixing Telegram Library Issue"
echo "================================"
echo ""

# The error is due to version incompatibility
# Let's reinstall with the correct version

echo "Uninstalling current telegram library..."
pip3 uninstall python-telegram-bot -y 2>/dev/null

echo "Installing compatible version..."
pip3 install "python-telegram-bot==21.3" --break-system-packages 2>/dev/null || pip3 install "python-telegram-bot==21.3"

echo ""
echo "✅ Library fixed!"
echo ""
echo "================================"
echo "🚀 Starting Bot with Fix"
echo "================================"
echo ""

# Load environment
export $(cat .env | grep -v '^#' | xargs)
export PG_CONNINFO="postgresql://mimerc:mimerc_secure_password@localhost:5433/mimerc_db"

echo "Starting MiMerc bot (fixed version)..."
echo "Press Ctrl+C to stop"
echo ""
echo "Once running, test in Telegram:"
echo "1. 'Add milk to my list'"
echo "2. 'Add eggs to my list'"
echo "3. 'What's on my list?' → Both should appear!"
echo ""

python3 telegram_bot.py
