#!/bin/bash
# Add test tasks via Lyco API

echo "📝 Adding test tasks to Lyco 2.0..."
echo ""

# Base URL
BASE_URL="http://localhost:8000"

# First, create some test signals that will become tasks
signals=(
  "Review Q1 financial reports and prepare executive summary"
  "Reply to Sarah's email about partnership proposal"
  "Schedule team 1:1s for next week"
  "Analyze competitor's new product launch"
  "Update LinkedIn profile with recent achievements"
  "Prepare board meeting presentation for Thursday"
  "Call dentist to reschedule appointment"
  "Review and approve marketing budget allocation"
)

sources=("email" "email" "calendar" "email" "task" "calendar" "task" "email")

# Add signals
for i in "${!signals[@]}"; do
  echo "Adding: ${signals[$i]:0:50}..."
  curl -X POST $BASE_URL/api/signals \
    -H "Content-Type: application/json" \
    -d "{\"source\": \"${sources[$i]}\", \"content\": \"${signals[$i]}\"}" \
    -s > /dev/null 2>&1
done

echo ""
echo "✅ Added ${#signals[@]} signals"
echo ""
echo "🤖 Triggering AI processing to convert signals to tasks..."
curl -X POST $BASE_URL/api/process -s > /dev/null 2>&1

echo ""
echo "✨ Done! Check your tasks at:"
echo "  - Main UI: http://localhost:8000"
echo "  - Rounds Mode: http://localhost:8000/rounds"
echo ""
echo "📊 To verify tasks were created:"
echo "  curl http://localhost:8000/api/status"
