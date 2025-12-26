#!/bin/bash
# Quick install and run script for MiMerc bot

echo "================================"
echo "📦 Installing MiMerc Dependencies"
echo "================================"
echo ""

# Use requirements.txt for proper versions
echo "Installing from requirements.txt..."
pip3 install -r requirements.txt --break-system-packages 2>/dev/null || pip3 install -r requirements.txt

if [ $? -eq 0 ]; then
    echo ""
    echo "✅ All dependencies installed successfully!"
else
    echo ""
    echo "⚠️  Some packages may have failed. Trying individual installs..."
    pip3 install python-telegram-bot==20.7 --break-system-packages 2>/dev/null || pip3 install python-telegram-bot==20.7
    pip3 install langchain langchain-openai langgraph --break-system-packages 2>/dev/null || pip3 install langchain langchain-openai langgraph
    pip3 install psycopg psycopg-pool --break-system-packages 2>/dev/null || pip3 install psycopg psycopg-pool
fi

echo ""
echo "================================"
echo "🚀 Starting Bot with Fix"
echo "================================"
echo ""

# Load environment
export $(cat .env | grep -v '^#' | xargs)
export PG_CONNINFO="postgresql://mimerc:mimerc_secure_password@localhost:5433/mimerc_db"

echo "Starting MiMerc bot..."
echo "Press Ctrl+C to stop"
echo ""

python3 telegram_bot.py
