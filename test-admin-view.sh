#!/bin/bash

# Test script for Lyco Admin View
echo "Testing Lyco Admin View Endpoints..."
echo "===================================="

BASE_URL="http://localhost:8000"

# Test 1: Get all tasks
echo -e "\n1. Testing GET /api/tasks/all"
echo "   Fetching all tasks..."
curl -s "$BASE_URL/api/tasks/all" | head -c 200
echo "..."

# Test 2: Get all tasks with energy filter
echo -e "\n\n2. Testing GET /api/tasks/all with energy filter"
echo "   Fetching high energy tasks..."
curl -s "$BASE_URL/api/tasks/all?filter_energy=high" | head -c 200
echo "..."

# Test 3: Get all tasks with status filter
echo -e "\n\n3. Testing GET /api/tasks/all with status filter"
echo "   Fetching parked tasks..."
curl -s "$BASE_URL/api/tasks/all?filter_status=parked" | head -c 200
echo "..."

# Test 4: Get all tasks sorted by skip_count
echo -e "\n\n4. Testing GET /api/tasks/all with sort"
echo "   Fetching tasks sorted by skip count..."
curl -s "$BASE_URL/api/tasks/all?sort_by=skip_count" | head -c 200
echo "..."

echo -e "\n\n===================================="
echo "Admin View Test Complete!"
echo ""
echo "To fully test the admin view:"
echo "1. Start Lyco server: cd agents/lyco/lyco-v2 && python server.py"
echo "2. Open admin view: http://localhost:8000/admin"
echo "3. Try filtering by energy level and status"
echo "4. Test quick actions: mark done, change energy, delete"
echo "5. Use search to find specific tasks"
echo "6. Check that stats update correctly"
