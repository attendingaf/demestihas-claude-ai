#!/bin/bash
# Install dependencies and restart bot with fix

echo "================================"
echo "🔧 MiMerc Bot Setup & Restart"
echo "================================"
echo ""

# Color codes
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

# Step 1: Check Python
echo -e "${YELLOW}Step 1: Checking Python installation...${NC}"
if command -v python3 &> /dev/null; then
    echo "✓ Python3 found: $(python3 --version)"
else
    echo -e "${RED}❌ Python3 not found. Please install Python 3.${NC}"
    exit 1
fi
echo ""

# Step 2: Install dependencies
echo -e "${YELLOW}Step 2: Installing required Python packages...${NC}"
echo "This may take a moment..."

# Check if pip3 is available
if ! command -v pip3 &> /dev/null; then
    echo "Installing pip3..."
    python3 -m ensurepip --default-pip
fi

# Install required packages
pip3 install --upgrade pip 2>/dev/null
echo "Installing telegram bot library..."
pip3 install python-telegram-bot --break-system-packages 2>/dev/null || pip3 install python-telegram-bot

echo "Installing LangChain and dependencies..."
pip3 install langchain langchain-openai langgraph psycopg psycopg-pool python-dotenv --break-system-packages 2>/dev/null || \
pip3 install langchain langchain-openai langgraph psycopg psycopg-pool python-dotenv

echo ""
echo -e "${GREEN}✓ Dependencies installed${NC}"
echo ""

# Step 3: Stop existing processes
echo -e "${YELLOW}Step 3: Stopping any existing bot processes...${NC}"
pkill -f telegram_bot.py 2>/dev/null && echo "Stopped existing telegram_bot.py" || echo "No existing bot running"
echo ""

# Step 4: Check PostgreSQL
echo -e "${YELLOW}Step 4: Checking PostgreSQL...${NC}"
if nc -z localhost 5433 2>/dev/null; then
    echo "✓ PostgreSQL is accessible on port 5433"
else
    echo -e "${YELLOW}⚠️  PostgreSQL not accessible on port 5433${NC}"
    echo ""
    echo "You need to start PostgreSQL. Options:"
    echo "1. If you have Docker Desktop:"
    echo "   - Start Docker Desktop"
    echo "   - Run: docker-compose up -d mimerc-postgres"
    echo ""
    echo "2. Or install PostgreSQL locally"
    echo ""
    echo -e "${RED}Cannot continue without database.${NC}"
    exit 1
fi
echo ""

# Step 5: Load environment and start bot
echo -e "${YELLOW}Step 5: Starting bot with persistence fix...${NC}"

# Load environment variables
if [ -f .env ]; then
    export $(cat .env | grep -v '^#' | xargs)
    echo "✓ Environment variables loaded"
else
    echo -e "${RED}❌ ERROR: .env file not found${NC}"
    exit 1
fi

# Override for local execution (PostgreSQL on mapped port)
export PG_CONNINFO="postgresql://mimerc:mimerc_secure_password@localhost:5433/mimerc_db"
echo "✓ Database connection configured"
echo ""

echo -e "${GREEN}================================${NC}"
echo -e "${GREEN}Starting MiMerc Telegram Bot${NC}"
echo -e "${GREEN}================================${NC}"
echo ""
echo "The bot will run in this terminal window."
echo "Press Ctrl+C to stop."
echo ""
echo "Once it starts, test with your Telegram bot:"
echo "1. Send: 'Add milk to my list'"
echo "2. Send: 'Add eggs to my list'"
echo "3. Send: 'What's on my list?'"
echo "   → Both items should appear!"
echo ""

# Start the bot
python3 telegram_bot.py
