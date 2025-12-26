#!/bin/bash
# Check MiMerc container status

echo "🔍 Checking MiMerc Container Status..."
echo "=================================="
echo ""

# Check if Docker is running
if ! docker info &> /dev/null; then
    echo "❌ Docker is not running!"
    echo "   Please start Docker Desktop"
    exit 1
fi

echo "✅ Docker is running"
echo ""

# Check all MiMerc containers
echo "📦 MiMerc Containers:"
echo "-------------------"

# Check PostgreSQL
if docker ps | grep -q "mimerc-postgres"; then
    echo "✅ mimerc-postgres: RUNNING"
    docker ps --format "table {{.Names}}\t{{.Status}}\t{{.Ports}}" | grep mimerc-postgres
else
    echo "❌ mimerc-postgres: NOT RUNNING"
    if docker ps -a | grep -q "mimerc-postgres"; then
        echo "   Container exists but is stopped"
    fi
fi

echo ""

# Check Telegram Bot
if docker ps | grep -q "mimerc-telegram"; then
    echo "✅ mimerc-telegram: RUNNING"
    docker ps --format "table {{.Names}}\t{{.Status}}\t{{.Ports}}" | grep mimerc-telegram
else
    echo "❌ mimerc-telegram: NOT RUNNING"
    if docker ps -a | grep -q "mimerc-telegram"; then
        echo "   Container exists but is stopped"
    fi
fi

echo ""

# Check Agent
if docker ps | grep -q "mimerc-agent"; then
    echo "✅ mimerc-agent: RUNNING"
    docker ps --format "table {{.Names}}\t{{.Status}}\t{{.Ports}}" | grep mimerc-agent
else
    echo "❌ mimerc-agent: NOT RUNNING"
    if docker ps -a | grep -q "mimerc-agent"; then
        echo "   Container exists but is stopped"
    fi
fi

echo ""
echo "=================================="
echo ""

# Quick health check
echo "🏥 Quick Health Check:"
echo "-------------------"

# Check if we can connect to postgres
if docker ps | grep -q "mimerc-postgres"; then
    if docker exec mimerc-postgres pg_isready -U mimerc -d mimerc_db &> /dev/null; then
        echo "✅ Database is responding"
    else
        echo "⚠️  Database container running but not responding"
    fi
fi

# Check recent logs for errors
echo ""
echo "📜 Recent Telegram Bot Logs (last 10 lines):"
echo "-------------------"
if docker ps | grep -q "mimerc-telegram"; then
    docker logs --tail 10 mimerc-telegram 2>&1
else
    echo "Cannot show logs - container not running"
fi

echo ""
echo "=================================="
echo ""

# Provide action recommendations
echo "🎯 Recommended Actions:"
if ! docker ps | grep -q "mimerc-telegram"; then
    echo "1. Start the Telegram bot:"
    echo "   docker-compose up -d mimerc-telegram"
fi

if ! docker ps | grep -q "mimerc-postgres"; then
    echo "1. Start the database:"
    echo "   docker-compose up -d mimerc-postgres"
fi

if docker ps | grep -q "mimerc-telegram" && docker ps | grep -q "mimerc-postgres"; then
    echo "✅ All essential services are running!"
    echo ""
    echo "If you're still seeing issues:"
    echo "1. Check logs: docker-compose logs -f mimerc-telegram"
    echo "2. Restart: docker-compose restart mimerc-telegram"
    echo "3. Rebuild: docker-compose build mimerc-telegram && docker-compose up -d mimerc-telegram"
fi
