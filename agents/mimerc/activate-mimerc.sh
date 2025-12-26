#!/bin/bash

# MiMerc Telegram Bot Activation Script
# Created: September 27, 2025

set -e

echo "🤖 MiMerc Telegram Bot Activation"
echo "=================================="
echo ""

# Check if we're in the right directory
if [ ! -f "telegram_bot.py" ]; then
    echo "❌ Error: Please run this script from the mimerc directory"
    exit 1
fi

# Check for .env file
if [ ! -f ".env" ]; then
    echo "❌ Error: .env file not found"
    exit 1
fi

# Check if token is already set
if grep -q "TELEGRAM_BOT_TOKEN=YOUR_BOT_TOKEN_HERE" .env; then
    echo "📝 Please enter your Telegram Bot Token"
    echo "   (Get this from @BotFather after creating your bot)"
    echo ""
    read -p "Token: " BOT_TOKEN
    
    if [ -z "$BOT_TOKEN" ]; then
        echo "❌ Error: Token cannot be empty"
        exit 1
    fi
    
    # Update the .env file with the actual token
    if [[ "$OSTYPE" == "darwin"* ]]; then
        # macOS
        sed -i '' "s/TELEGRAM_BOT_TOKEN=YOUR_BOT_TOKEN_HERE/TELEGRAM_BOT_TOKEN=$BOT_TOKEN/" .env
    else
        # Linux
        sed -i "s/TELEGRAM_BOT_TOKEN=YOUR_BOT_TOKEN_HERE/TELEGRAM_BOT_TOKEN=$BOT_TOKEN/" .env
    fi
    
    echo "✅ Token saved to .env file"
    echo ""
else
    echo "✅ Telegram bot token already configured"
    echo ""
fi

# Choose deployment method
echo "How would you like to run MiMerc?"
echo "1) Docker (Recommended)"
echo "2) Local Python"
echo ""
read -p "Choice [1-2]: " CHOICE

case $CHOICE in
    1)
        echo ""
        echo "🐳 Starting MiMerc with Docker..."
        echo ""
        
        # Check if Docker is running
        if ! docker info &> /dev/null; then
            echo "❌ Error: Docker is not running"
            echo "   Please start Docker Desktop and try again"
            exit 1
        fi
        
        # Check if database is needed
        if ! docker ps | grep -q "mimerc-postgres"; then
            echo "📦 Starting PostgreSQL database..."
            docker-compose up -d mimerc-postgres
            echo "⏳ Waiting for database to be ready..."
            sleep 5
        fi
        
        # Build and start the bot
        echo "🔨 Building MiMerc containers..."
        docker-compose build mimerc-telegram
        
        echo "🚀 Starting MiMerc Telegram bot..."
        docker-compose up -d mimerc-telegram
        
        echo ""
        echo "✅ MiMerc is running in Docker!"
        echo ""
        echo "📊 Check status with:"
        echo "   docker-compose ps"
        echo ""
        echo "📜 View logs with:"
        echo "   docker-compose logs -f mimerc-telegram"
        echo ""
        echo "🛑 Stop with:"
        echo "   docker-compose stop mimerc-telegram"
        ;;
        
    2)
        echo ""
        echo "🐍 Starting MiMerc locally..."
        echo ""
        
        # Check Python
        if ! command -v python3 &> /dev/null; then
            echo "❌ Error: Python 3 is not installed"
            exit 1
        fi
        
        # Install dependencies
        echo "📦 Installing Python dependencies..."
        pip3 install -r requirements.txt
        
        # Check if database is running
        if ! pg_isready -h localhost -p 5432 &> /dev/null; then
            echo "⚠️  Warning: PostgreSQL doesn't seem to be running"
            echo "   The bot needs a PostgreSQL database to store data"
            echo ""
            echo "   Option 1: Start PostgreSQL locally"
            echo "   Option 2: Use Docker for the database:"
            echo "             docker-compose up -d mimerc-postgres"
            echo ""
            read -p "Continue anyway? [y/N]: " CONTINUE
            if [ "$CONTINUE" != "y" ] && [ "$CONTINUE" != "Y" ]; then
                exit 0
            fi
        fi
        
        echo ""
        echo "🚀 Starting MiMerc bot..."
        echo ""
        python3 telegram_bot.py
        ;;
        
    *)
        echo "❌ Invalid choice"
        exit 1
        ;;
esac

echo ""
echo "🎉 MiMerc Telegram Bot is Active!"
echo ""
echo "📱 Next Steps:"
echo "   1. Open Telegram"
echo "   2. Search for your bot by username"
echo "   3. Send /start to begin"
echo "   4. Try: 'Add milk and eggs to my list'"
echo ""
echo "👨‍👩‍👧‍👦 To use in a group chat:"
echo "   1. Add your bot to the group"
echo "   2. Make it an admin (optional, for better features)"
echo "   3. Everyone can now share the grocery list!"
echo ""
echo "📋 Available Commands:"
echo "   /start - Welcome message"
echo "   /list - View grocery list"
echo "   /add [items] - Add items"
echo "   /remove [items] - Remove items"
echo "   /clear - Clear the list"
echo "   /help - Show commands"
echo ""
echo "Happy shopping! 🛒"
