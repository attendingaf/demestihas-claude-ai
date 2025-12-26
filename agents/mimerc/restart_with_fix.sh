#!/bin/bash
# Complete bot restart with the persistence fix

echo "================================"
echo "🔧 MiMerc Bot Complete Restart"
echo "================================"
echo ""
echo "This will ensure your bot runs with the state persistence fix."
echo ""

# Color codes for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Step 1: Kill any existing bot processes
echo -e "${YELLOW}Step 1: Stopping any existing bot processes...${NC}"
pkill -f telegram_bot.py 2>/dev/null && echo "Stopped existing telegram_bot.py" || echo "No existing telegram_bot.py running"
pkill -f mimerc 2>/dev/null && echo "Stopped existing mimerc processes" || echo "No existing mimerc processes"
echo ""

# Step 2: Check if Docker is available and running
echo -e "${YELLOW}Step 2: Checking Docker status...${NC}"
if pgrep -x "Docker" > /dev/null; then
    echo "Docker Desktop is running"
    
    # Find docker command
    DOCKER_CMD=""
    if [ -f "/usr/local/bin/docker" ]; then
        DOCKER_CMD="/usr/local/bin/docker"
    elif [ -f "/Applications/Docker.app/Contents/Resources/bin/docker" ]; then
        DOCKER_CMD="/Applications/Docker.app/Contents/Resources/bin/docker"
    fi
    
    if [ ! -z "$DOCKER_CMD" ]; then
        DOCKER_COMPOSE_CMD="${DOCKER_CMD}-compose"
        if ! command -v docker-compose &> /dev/null; then
            DOCKER_COMPOSE_CMD="${DOCKER_CMD} compose"
        fi
        
        echo "Stopping Docker containers..."
        $DOCKER_COMPOSE_CMD down 2>/dev/null || echo "No containers to stop"
        
        echo "Rebuilding with fixed code..."
        $DOCKER_COMPOSE_CMD build
        
        echo -e "${GREEN}Starting fresh containers with the fix...${NC}"
        $DOCKER_COMPOSE_CMD up -d
        
        echo ""
        echo -e "${GREEN}✅ Bot restarted in Docker with persistence fix!${NC}"
        echo ""
        echo "Test it now:"
        echo "1. Send to your bot: 'Add milk to my list'"
        echo "2. Send: 'Add eggs to my list'"
        echo "3. Send: 'What's on my list?'"
        echo "4. You should see BOTH items!"
        
        # Check logs
        echo ""
        echo "Showing bot logs (Ctrl+C to exit):"
        $DOCKER_COMPOSE_CMD logs -f mimerc-telegram
    fi
else
    echo -e "${YELLOW}Docker Desktop not running. Starting bot locally...${NC}"
    echo ""
    
    # Step 3: Start locally
    echo -e "${YELLOW}Step 3: Starting bot locally with Python...${NC}"
    
    # Load environment variables
    if [ -f .env ]; then
        export $(cat .env | grep -v '^#' | xargs)
        echo "✓ Environment variables loaded"
    else
        echo -e "${RED}❌ ERROR: .env file not found${NC}"
        exit 1
    fi
    
    # Check for PostgreSQL
    echo "Checking PostgreSQL..."
    if nc -z localhost 5433 2>/dev/null; then
        echo "✓ PostgreSQL is accessible on port 5433"
    else
        echo -e "${YELLOW}⚠️  PostgreSQL not accessible on port 5433${NC}"
        echo "Starting PostgreSQL container..."
        
        # Try to start just PostgreSQL
        if [ ! -z "$DOCKER_CMD" ]; then
            $DOCKER_COMPOSE_CMD up -d mimerc-postgres
            echo "Waiting for PostgreSQL to be ready..."
            sleep 5
        else
            echo -e "${RED}❌ Cannot start PostgreSQL - Docker not available${NC}"
            echo "Please start Docker Desktop and run this script again."
            exit 1
        fi
    fi
    
    # Override connection string for local execution
    export PG_CONNINFO="postgresql://mimerc:mimerc_secure_password@localhost:5433/mimerc_db"
    echo "✓ Database connection configured for local execution"
    
    # Start the bot
    echo ""
    echo -e "${GREEN}Starting telegram bot with persistence fix...${NC}"
    echo "Bot will run in foreground. Press Ctrl+C to stop."
    echo ""
    
    python3 telegram_bot.py
fi
