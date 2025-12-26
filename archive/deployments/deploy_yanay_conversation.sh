#!/bin/bash
# Yanay.ai Conversational Enhancement Deployment
# Execute Time: ~10 minutes

echo "🚀 Yanay.ai Conversational Enhancement Deployment"
echo "================================================"

# Configuration
VPS_IP="178.156.170.161"
PROJECT_DIR="/root/demestihas-ai"
BACKUP_SUFFIX=$(date +%Y%m%d_%H%M%S)

echo "📦 Step 1: Uploading enhancement files..."
# Upload the three new files
scp ~/Projects/demestihas-ai/conversation_manager.py root@$VPS_IP:$PROJECT_DIR/
scp ~/Projects/demestihas-ai/token_manager.py root@$VPS_IP:$PROJECT_DIR/
scp ~/Projects/demestihas-ai/yanay_enhancement_patch.py root@$VPS_IP:$PROJECT_DIR/

echo "🔧 Step 2: Applying configuration..."
# Add environment variables
ssh root@$VPS_IP << 'ENDSSH'
cd /root/demestihas-ai

# Backup current yanay.py
cp yanay.py yanay.py.backup.$(date +%Y%m%d_%H%M%S)

# Add Opus configuration to .env if not present
if ! grep -q "ANTHROPIC_OPUS_KEY" .env; then
    echo "" >> .env
    echo "# Opus Configuration for Conversations" >> .env
    echo "ANTHROPIC_OPUS_KEY=${ANTHROPIC_API_KEY}" >> .env
    echo "DAILY_TOKEN_LIMIT=15" >> .env
fi

# Install missing dependency
pip install nest-asyncio

echo "✅ Configuration applied"
ENDSSH

echo "📝 Step 3: Manual integration required..."
echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "MANUAL STEPS REQUIRED (5 minutes):"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""
echo "1. SSH into VPS:"
echo "   ssh root@$VPS_IP"
echo ""
echo "2. Navigate to project:"
echo "   cd $PROJECT_DIR"
echo ""
echo "3. Edit yanay.py and add imports at top:"
echo "   nano yanay.py"
echo ""
echo "   ADD THESE LINES AFTER EXISTING IMPORTS:"
echo "   from conversation_manager import ConversationStateManager"
echo "   from token_manager import TokenBudgetManager"
echo "   from anthropic import Anthropic"
echo ""
echo "4. In the __init__ method, add:"
echo "   self.conversation_manager = ConversationStateManager()"
echo "   self.token_manager = TokenBudgetManager()"
echo "   self.opus_client = Anthropic(api_key=os.getenv('ANTHROPIC_OPUS_KEY'))"
echo ""
echo "5. Find the main message processing method and add intelligent routing:"
echo "   - Look for where messages are processed"
echo "   - Add decision = await self.evaluate_response_mode(message, user_id)"
echo "   - Route based on decision mode"
echo ""
echo "6. Copy methods from yanay_enhancement_patch.py:"
echo "   - evaluate_response_mode"
echo "   - opus_conversation"
echo "   - enhanced_process_message"
echo ""
echo "7. Save and exit (Ctrl+X, Y, Enter)"
echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"

echo ""
echo "🐳 Step 4: Restart Yanay container (after manual edits):"
echo "   docker-compose restart yanay"
echo ""
echo "📊 Step 5: Monitor logs:"
echo "   docker logs -f demestihas-yanay"
echo ""
echo "✅ Step 6: Test conversation:"
echo "   Send to @LycurgusBot: 'I'm feeling stressed about my meetings today'"
echo "   Expected: Warm, supportive Opus response with context"
echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
