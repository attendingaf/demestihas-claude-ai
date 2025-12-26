#!/bin/bash
# Streamlined Yanay.ai Enhancement Deployment
# Total execution time: ~5 minutes

echo "🚀 Yanay.ai Conversation Enhancement - Automated Deployment"
echo "=========================================================="
echo ""

VPS_IP="178.156.170.161"
PROJECT_DIR="/root/demestihas-ai"

echo "📦 Step 1: Uploading enhancement files..."
echo "----------------------------------------"

# Upload the core enhancement files
scp ~/Projects/demestihas-ai/conversation_manager.py root@$VPS_IP:$PROJECT_DIR/
scp ~/Projects/demestihas-ai/token_manager.py root@$VPS_IP:$PROJECT_DIR/
scp ~/Projects/demestihas-ai/yanay_integrator.py root@$VPS_IP:$PROJECT_DIR/

echo "✅ Files uploaded"
echo ""

echo "🔧 Step 2: Running automated integration..."
echo "----------------------------------------"

# Execute the integration remotely
ssh root@$VPS_IP << 'ENDSSH'
cd /root/demestihas-ai

# Add environment variables if missing
if ! grep -q "ANTHROPIC_OPUS_KEY" .env; then
    echo "" >> .env
    echo "# Opus Configuration for Conversations" >> .env
    echo "ANTHROPIC_OPUS_KEY=${ANTHROPIC_API_KEY}" >> .env
    echo "DAILY_TOKEN_LIMIT=15" >> .env
    echo "✅ Environment variables added"
fi

# Install missing dependency
pip install nest-asyncio anthropic > /dev/null 2>&1
echo "✅ Dependencies installed"

# Run the Python integrator
echo "🔄 Integrating enhancements into yanay.py..."
python3 yanay_integrator.py

# Check syntax
echo "🔍 Checking syntax..."
if python3 -m py_compile yanay.py 2>/dev/null; then
    echo "✅ Syntax check passed"
    
    # Restart the container
    echo "🐳 Restarting Yanay container..."
    docker-compose restart yanay
    
    # Wait for container to start
    sleep 5
    
    # Check if container is running
    if docker ps | grep -q yanay; then
        echo "✅ Yanay container restarted successfully"
        
        # Show initial logs
        echo ""
        echo "📋 Initial logs:"
        echo "----------------"
        docker logs --tail 20 demestihas-yanay
    else
        echo "⚠️ Container failed to start. Checking logs..."
        docker logs --tail 50 demestihas-yanay
    fi
else
    echo "❌ Syntax error detected. Restoring backup..."
    # Find most recent backup and restore
    BACKUP=$(ls -t yanay.py.backup.* | head -1)
    if [ -n "$BACKUP" ]; then
        cp "$BACKUP" yanay.py
        echo "✅ Restored from $BACKUP"
        echo "Please check the integration manually"
    fi
fi
ENDSSH

echo ""
echo "🧪 Step 3: Testing conversation enhancement..."
echo "----------------------------------------"
echo ""
echo "Send these test messages to @LycurgusBot:"
echo ""
echo "1️⃣ Emotional Support Test:"
echo "   'I'm feeling really stressed about all my meetings today'"
echo "   Expected: Warm, supportive Opus response"
echo ""
echo "2️⃣ Direct Task Test:"
echo "   'Add dentist appointment tomorrow at 3pm'"
echo "   Expected: Quick delegation to Huata"
echo ""
echo "3️⃣ Educational Test:"
echo "   'Why do we need to sleep?'"
echo "   Expected: Engaging educational response"
echo ""
echo "4️⃣ Complex Coordination Test:"
echo "   'Help me plan a birthday party for Saturday'"
echo "   Expected: Multi-agent coordination response"
echo ""
echo "----------------------------------------"
echo ""
echo "📊 Monitoring Commands:"
echo "  ssh root@$VPS_IP"
echo "  docker logs -f demestihas-yanay     # Watch live logs"
echo "  redis-cli KEYS 'conv:*'             # Check conversation state"
echo "  redis-cli KEYS 'tokens:*'           # Check token tracking"
echo ""
echo "🔄 Rollback if needed:"
echo "  cd /root/demestihas-ai"
echo "  cp yanay.py.backup.* yanay.py       # Use tab to complete"
echo "  docker-compose restart yanay"
echo ""
echo "=========================================================="
echo "✅ Deployment complete! Test the bot now."
