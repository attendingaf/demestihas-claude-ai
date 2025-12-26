#!/bin/bash
# VPS Deployment Script - Calendar Intent Routing Fix
# Execute this on the VPS at /root/demestihas-ai

echo "🚀 Starting Calendar Intent Routing Fix Deployment"
echo "=================================================="

# Step 1: Verify we're in the right directory
if [[ "$PWD" != "/root/demestihas-ai" ]]; then
    echo "❌ ERROR: Must be in /root/demestihas-ai directory"
    exit 1
fi

# Step 2: Backup current yanay.py
echo "📦 Creating backup..."
cp yanay.py yanay.py.backup.$(date +%Y%m%d_%H%M%S)
echo "✅ Backup created"

# Step 3: Apply the fix manually (requires manual editing)
echo "⚠️  MANUAL STEP REQUIRED:"
echo "   1. Edit yanay.py"
echo "   2. Find the 'contains_calendar_intent' method"
echo "   3. Replace the calendar_keywords list to include these missing keywords:"
echo "      'event', 'events', 'meeting', 'meetings', 'appointment', 'appointments',"
echo "   4. Add them at the start of the '# Event/meeting references' section"

# Step 4: After manual edit, rebuild containers
echo ""
echo "🔄 After manual edit, run these commands:"
echo "docker-compose down yanay"
echo "docker-compose up -d --build yanay"
echo "docker logs yanay --tail 20"

# Step 5: Test commands
echo ""
echo "📱 Then test via @LycurgusBot:"
echo "   - 'what on my calendar today?'"
echo "   - 'whats on my calendar tomorrow?'"
echo "   - Should get calendar responses, NOT '400' errors"

echo ""
echo "✅ Deployment script complete. Please execute manual steps above."
