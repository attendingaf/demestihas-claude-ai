#!/bin/bash
# Force activate a task for display

echo "🔄 Activating first task in queue..."

# Get the first task ID from queue
TASK_ID=$(curl -s http://localhost:8000/api/queue-preview | python3 -c "
import json, sys
data = json.load(sys.stdin)
if data.get('queue'):
    print(data['queue'][0]['id'])
")

if [ -z "$TASK_ID" ]; then
    echo "❌ No tasks found in queue"
    exit 1
fi

echo "📝 Task ID: $TASK_ID"

# Try to get this specific task as "next"
echo "🎯 Setting as next task..."
curl -s http://localhost:8000/api/next-task

echo ""
echo "✅ Try refreshing the main UI now:"
echo "   http://localhost:8000"
echo ""
echo "Or go directly to Rounds Mode:"
echo "   http://localhost:8000/rounds"
