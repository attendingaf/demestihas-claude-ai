#!/bin/bash
# Clean restart script for MiMerc - handles orphaned containers

echo "🧹 MiMerc Clean Restart Script"
echo "=============================="

# Step 1: Stop ALL MiMerc containers
echo "Step 1: Stopping all MiMerc containers..."
docker stop mimerc-postgres mimerc-agent 2>/dev/null || true

# Step 2: Remove ALL MiMerc containers
echo "Step 2: Removing old containers..."
docker rm -f mimerc-postgres mimerc-agent 2>/dev/null || true

# Step 3: Remove orphan containers
echo "Step 3: Cleaning orphaned containers..."
docker-compose down --remove-orphans

# Step 4: Remove the old volume for fresh start
echo "Step 4: Removing old database volume..."
docker volume rm mimerc_postgres_data 2>/dev/null || true

# Step 5: Verify cleanup
echo "Step 5: Verifying cleanup..."
docker ps -a | grep mimerc && echo "⚠️ Still have mimerc containers!" || echo "✅ All mimerc containers removed"

# Step 6: Check if .env has real API key
echo "Step 6: Checking API key..."
if grep -q "sk-YOUR_ACTUAL_OPENAI_API_KEY_HERE" .env 2>/dev/null; then
    echo "⚠️  WARNING: You still need to add your OpenAI API key to .env!"
    echo "   Edit .env and replace sk-YOUR_ACTUAL_OPENAI_API_KEY_HERE"
    echo ""
    read -p "Have you added your OpenAI API key to .env? (y/n): " -n 1 -r
    echo
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        echo "❌ Please add your API key first:"
        echo "   nano .env"
        echo "   Then run this script again"
        exit 1
    fi
else
    echo "✅ API key appears to be set"
fi

# Step 7: Start fresh with build
echo "Step 7: Building and starting fresh containers..."
docker-compose up --build -d

# Step 8: Wait for containers to be ready
echo "Step 8: Waiting for services to start..."
sleep 10

# Step 9: Check container status
echo "Step 9: Checking container status..."
docker ps --format "table {{.Names}}\t{{.Status}}" | grep mimerc

# Step 10: Check if tables were created
echo "Step 10: Verifying database tables..."
sleep 5
docker exec mimerc-postgres psql -U mimerc -d mimerc_db -c "\dt" 2>/dev/null | grep checkpoint && echo "✅ Tables created!" || echo "⚠️ Tables might still be creating..."

# Step 11: Check agent logs
echo "Step 11: Checking agent logs..."
docker logs mimerc-agent --tail 10

echo ""
echo "🎯 Next Steps:"
echo "=============="
echo "1. If you see errors about API key, edit .env"
echo "2. If you see database errors, wait 30 seconds and check again"
echo "3. Run ./test-mimerc.sh to test functionality"
echo ""
echo "To view logs:"
echo "  docker logs -f mimerc-agent    # Agent logs"
echo "  docker logs -f mimerc-postgres  # Database logs"
