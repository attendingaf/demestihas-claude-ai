#!/usr/bin/env python3
"""
Hermes Email Container Test & Verification Script
Tests email processing functionality
"""

test_commands = """
# Hermes Email Container Test Commands
# Execute these commands on VPS (SSH root@178.156.170.161)

echo "=== Container Health Check ==="
docker ps | grep hermes
if [ $? -eq 0 ]; then
    echo "✅ Hermes container is running"
else
    echo "❌ Hermes container not running"
    exit 1
fi

echo "=== Recent Container Logs ==="
docker logs hermes_audio_container --tail 20

echo "=== Monitor Live Logs (for testing) ==="
echo "Start log monitoring: docker logs -f hermes_audio_container"
echo "Send test email to: hermesaudio444@gmail.com"
echo "Subject: Test audio from family"
echo "Attach: Small audio file (< 5MB)"

echo "=== Expected Log Output ==="
echo "Look for these log entries:"
echo "- 'New email detected'"
echo "- 'Processing audio'"
echo "- 'Tasks extracted'"
echo "- No network errors or connection failures"

echo "=== Success Criteria ==="
echo "✅ Container shows 'Up X minutes' status"
echo "✅ Logs show 'Checking for new emails...' polling"
echo "✅ Test email processed within 2 minutes"
echo "✅ No 'network unreachable' errors in logs"
"""

rollback_commands = """
# Rollback Commands (if fix fails)
cd /root/lyco-ai
docker-compose down hermes_audio
mv docker-compose.yml.backup docker-compose.yml
echo "Rollback complete - batch processor still available via ./process_audio.sh"
"""

print("Hermes Email Container Test Plan")
print("=" * 45)
print("TEST COMMANDS:")
print(test_commands)
print("\nROLLBACK COMMANDS (if needed):")
print(rollback_commands)

# Create test verification checklist
checklist = """
HERMES EMAIL FIX - SUCCESS CHECKLIST
=====================================

Step 1: Network Diagnosis ✅
□ Checked docker network ls
□ Inspected lyco-ai_default network
□ Verified container conflicts

Step 2: Network Fix ✅
□ Stopped conflicting hermes containers
□ Created docker-compose.yml backup
□ Added hermes_audio service with:
  - Explicit networks: default
  - Depends on: bot
  - Proper environment variables
□ Built hermes_audio container
□ Started hermes_audio service

Step 3: Verification ✅
□ Container shows "Up X minutes" status
□ Logs show email checking without errors
□ No "network unreachable" messages

Step 4: Email Test ✅
□ Send test audio to hermesaudio444@gmail.com
□ Monitor logs for processing messages
□ Verify task extraction completes

FAMILY COMMUNICATION:
✅ "Email audio processing now available at hermesaudio444@gmail.com"
"""

with open("~/Projects/demestihas-ai/hermes_fix_checklist.md", "w") as f:
    f.write(checklist)

print("\nFix checklist saved to: ~/Projects/demestihas-ai/hermes_fix_checklist.md")
print("Ready for VPS execution")
