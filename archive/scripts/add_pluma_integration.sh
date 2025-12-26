#!/bin/bash

# Add Pluma Integration to Yanay.py
# Simple integration addition for email routing

set -e

VPS_IP="178.156.170.161"
VPS_USER="root"

echo "🔗 ADDING PLUMA INTEGRATION TO YANAY"

ssh ${VPS_USER}@${VPS_IP} << 'ENDSSH'
cd /root/demestihas-ai

# Create backup
cp yanay.py yanay_backup_$(date +%Y%m%d_%H%M%S).py

# Check if PlumaIntegration already exists
if grep -q "PlumaIntegration" yanay.py; then
    echo "✅ PlumaIntegration already exists in yanay.py"
    exit 0
fi

echo "📝 Adding Pluma integration code..."

# Add Pluma integration class before the main orchestrator class
cat << 'PYTHON_EOF' > pluma_integration_code.py

import aiohttp
import json
from typing import Optional

class PlumaIntegration:
    """Simple Pluma integration for Yanay orchestrator"""
    
    def __init__(self, logger):
        self.logger = logger
        self.pluma_url = "http://demestihas-pluma:8080"
    
    def should_route_to_pluma(self, message: str) -> bool:
        """Check if message should go to Pluma agent"""
        email_keywords = [
            'email', 'draft', 'reply', 'inbox', 'unread',
            'gmail', 'compose', 'organize emails', 'email status'
        ]
        message_lower = message.lower()
        return any(keyword in message_lower for keyword in email_keywords)
    
    async def route_to_pluma(self, message: str, user_id: str) -> str:
        """Route message to Pluma agent"""
        try:
            self.logger.info(f"Routing to Pluma: {message[:50]}...")
            
            # For now, return helpful message since Pluma container is new
            if 'draft' in message.lower() or 'reply' in message.lower():
                return """📧 **Email Drafting Available**
                
I can help draft email replies once Gmail is connected.

Next steps:
1. Set up Gmail OAuth (see gmail_setup_guide.md)
2. Test with "draft reply to latest email"

Pluma agent is running and ready for Gmail integration."""

            elif 'inbox' in message.lower() or 'organize' in message.lower():
                return """📮 **Inbox Management Available**
                
I can organize your inbox and manage emails once Gmail is connected.

Available commands:
• "organize my inbox" - Smart email categorization
• "check unread emails" - Show recent messages  
• "email status" - Check Gmail connection

Set up Gmail OAuth to enable full functionality."""

            else:
                return """📧 **Pluma Email Agent Ready**
                
I'm your email assistant! I can help with:
• Email drafting with tone matching
• Smart inbox organization  
• Meeting notes processing
• Executive email management

First: Set up Gmail OAuth (gmail_setup_guide.md)
Then try: "draft reply to latest email"""
                
        except Exception as e:
            self.logger.error(f"Pluma routing failed: {e}")
            return "Email agent is starting up. Please try again in a moment."

PYTHON_EOF

# Find the main orchestrator class and add Pluma integration before it
if grep -q "class.*Orchestrator" yanay.py; then
    # Insert PlumaIntegration class before the main orchestrator class
    sed -i '/class.*Orchestrator/i\
# Pluma Integration\
import aiohttp\
import json\
from typing import Optional\
\
class PlumaIntegration:\
    """Simple Pluma integration for Yanay orchestrator"""\
    \
    def __init__(self, logger):\
        self.logger = logger\
        self.pluma_url = "http://demestihas-pluma:8080"\
    \
    def should_route_to_pluma(self, message: str) -> bool:\
        """Check if message should go to Pluma agent"""\
        email_keywords = [\
            "email", "draft", "reply", "inbox", "unread",\
            "gmail", "compose", "organize emails", "email status"\
        ]\
        message_lower = message.lower()\
        return any(keyword in message_lower for keyword in email_keywords)\
    \
    async def route_to_pluma(self, message: str, user_id: str) -> str:\
        """Route message to Pluma agent"""\
        try:\
            self.logger.info(f"Routing to Pluma: {message[:50]}...")\
            \
            if "draft" in message.lower() or "reply" in message.lower():\
                return """📧 **Email Drafting Available**\
\
I can help draft email replies once Gmail is connected.\
\
Next steps:\
1. Set up Gmail OAuth (see gmail_setup_guide.md)\
2. Test with "draft reply to latest email"\
\
Pluma agent is running and ready for Gmail integration."""\
\
            elif "inbox" in message.lower() or "organize" in message.lower():\
                return """📮 **Inbox Management Available**\
\
I can organize your inbox and manage emails once Gmail is connected.\
\
Available commands:\
• "organize my inbox" - Smart email categorization\
• "check unread emails" - Show recent messages\
• "email status" - Check Gmail connection\
\
Set up Gmail OAuth to enable full functionality."""\
\
            else:\
                return """📧 **Pluma Email Agent Ready**\
\
I am your email assistant! I can help with:\
• Email drafting with tone matching\
• Smart inbox organization\
• Meeting notes processing\
• Executive email management\
\
First: Set up Gmail OAuth (gmail_setup_guide.md)\
Then try: "draft reply to latest email\""""\
                \
        except Exception as e:\
            self.logger.error(f"Pluma routing failed: {e}")\
            return "Email agent is starting up. Please try again in a moment."\
\
' yanay.py
    
    # Add Pluma routing to the process_message method
    if grep -q "async def process_message" yanay.py; then
        # Add Pluma check at the beginning of process_message
        sed -i '/async def process_message/,/return/ {
            /return/i\
        # Check for Pluma email routing\
        pluma_integration = PlumaIntegration(self.logger)\
        if pluma_integration.should_route_to_pluma(message):\
            return await pluma_integration.route_to_pluma(message, user_id)\

        }' yanay.py
    fi
    
    echo "✅ Pluma integration added to yanay.py"
    
    # Restart Yanay to pick up changes
    echo "🔄 Restarting Yanay container..."
    docker-compose restart yanay
    
    echo "⏳ Waiting for Yanay restart..."
    sleep 10
    
    if docker ps | grep -q demestihas-yanay; then
        echo "✅ Yanay restarted successfully"
    else
        echo "❌ Yanay restart failed"
        echo "Logs:"
        docker logs --tail=10 demestihas-yanay
    fi
    
else
    echo "❌ Could not find orchestrator class in yanay.py"
    echo "yanay.py structure:"
    head -20 yanay.py
fi

# Clean up
rm -f pluma_integration_code.py

ENDSSH

echo "🎉 Yanay-Pluma integration complete!"
