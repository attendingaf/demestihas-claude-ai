#!/bin/bash
echo "🧪 Testing Email-to-Task Integration"

# Test 1: Health check
echo "1️⃣ Testing health endpoint..."
curl -s http://localhost:8090/health | python3 -m json.tool
if [ $? -eq 0 ]; then
    echo "✅ Health check passed"
else
    echo "❌ Health check failed"
fi
echo ""

# Test 2: Queue status
echo "2️⃣ Testing queue status..."
curl -s http://localhost:8090/queue/status | python3 -m json.tool
echo ""

# Test 3: Simple email webhook test
echo "3️⃣ Testing simple email parsing..."
curl -X POST http://localhost:8090/email/webhook \
  -H "Content-Type: application/json" \
  -d '{
    "from": "test@example.com",
    "subject": "Review Q3 report",
    "text": "Please review the attached Q3 report by Friday. Let me know if you have questions.",
    "to": "tasks@demestihas.com"
  }'
echo ""
echo ""

# Test 4: Multiple tasks email
echo "4️⃣ Testing multiple tasks email..."
curl -X POST http://localhost:8090/email/webhook \
  -H "Content-Type: application/json" \
  -d '{
    "from": "manager@company.com",
    "subject": "Project updates needed",
    "text": "Hi, we need to: 1) Update the dashboard by EOD, 2) Schedule team meeting for next week, 3) Send status report to board",
    "to": "tasks@demestihas.com"
  }'
echo ""
echo ""

# Test 5: Wait and check queue status
echo "5️⃣ Waiting for processing..."
sleep 5
echo "Queue status after processing:"
curl -s http://localhost:8090/queue/status | python3 -m json.tool
echo ""

# Test 6: Docker logs
echo "6️⃣ Recent service logs:"
docker logs --tail 20 demestihas-email
echo ""

echo "🎯 Email integration testing complete!"
echo ""
echo "If tests pass, email forwarding is ready for:"
echo "- Simple task extraction (Test 3)"  
echo "- Multiple task handling (Test 4)"
echo "- Queue processing (Test 5)"
echo ""
echo "Next: Set up SendGrid webhook pointing to http://178.156.170.161:8090/email/webhook"
