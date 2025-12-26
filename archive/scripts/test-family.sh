#!/bin/bash

# Family Context Validation Script
# Tests family profiles, templates, and personalization

echo "==================================="
echo "Claude Desktop Family AI"
echo "Family Context Validation Test"
echo "==================================="
echo ""

# Color codes for output
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Test counters
TOTAL_TESTS=0
PASSED_TESTS=0
FAILED_TESTS=0

# Test function
run_test() {
    local test_name="$1"
    local test_command="$2"
    local expected="$3"
    
    TOTAL_TESTS=$((TOTAL_TESTS + 1))
    echo -n "Testing: $test_name..."
    
    if eval "$test_command"; then
        echo -e " ${GREEN}✓${NC}"
        PASSED_TESTS=$((PASSED_TESTS + 1))
    else
        echo -e " ${RED}✗${NC}"
        FAILED_TESTS=$((FAILED_TESTS + 1))
        echo "  Expected: $expected"
    fi
}

echo "[Phase 1] File Existence Tests"
echo "--------------------------------"

# Check new files exist
run_test "family.md exists" "[ -f family.md ]" "File should exist"
run_test "templates.md exists" "[ -f templates.md ]" "File should exist"

# Check file sizes (ensure they're not empty)
run_test "family.md not empty" "[ -s family.md ]" "File should contain content"
run_test "templates.md not empty" "[ -s templates.md ]" "File should contain content"

echo ""
echo "[Phase 2] Content Validation"
echo "--------------------------------"

# Check family member profiles
run_test "Demestihas profile" "grep -q 'demestihas:' family.md" "Profile should exist"
run_test "Angela profile" "grep -q 'angela:' family.md" "Profile should exist"
run_test "Children profile" "grep -q 'CHILD_PROFILES:' family.md" "Profile should exist"

# Check template categories
run_test "Greeting templates" "grep -q 'GREETINGS:' templates.md" "Templates should exist"
run_test "Error templates" "grep -q 'ERRORS:' templates.md" "Templates should exist"
run_test "Success templates" "grep -q 'SUCCESS:' templates.md" "Templates should exist"

echo ""
echo "[Phase 3] Integration Tests"
echo "--------------------------------"

# Check bootstrap integration
run_test "Bootstrap updated" "grep -q 'family.md' bootstrap.md" "Family file in bootstrap"
run_test "Templates in bootstrap" "grep -q 'templates.md' bootstrap.md" "Templates in bootstrap"
run_test "Family init hooks" "grep -q 'FAMILY_INIT:' bootstrap.md" "Family init configured"
run_test "Lazy load strategy" "grep -q 'loadFamilyContext' bootstrap.md" "Lazy loading implemented"

echo ""
echo "[Phase 4] Safety & Privacy Tests"
echo "--------------------------------"

# Check safety protocols
run_test "Child safety rules" "grep -q 'safety_mode: \"strict\"' family.md" "Child safety enabled"
run_test "Permission system" "grep -q 'require_permission: true' family.md" "Permissions configured"
run_test "Content filtering" "grep -q 'content_filter:' family.md" "Content filter present"
run_test "Privacy isolation" "grep -q 'member_isolation:' family.md" "Privacy rules defined"

echo ""
echo "[Phase 5] Personalization Tests"
echo "--------------------------------"

# Check personalization features
run_test "Technical shortcuts" "grep -q '\"check\": \"git status' family.md" "Demestihas shortcuts"
run_test "Simple shortcuts" "grep -q '\"show\": \"display with' family.md" "Angela shortcuts"
run_test "Response styles" "grep -q 'preferred_style:' family.md" "Style preferences set"
run_test "Learning patterns" "grep -q 'PATTERN_LEARNING:' family.md" "Learning configured"

echo ""
echo "[Phase 6] Template Diversity Tests"
echo "--------------------------------"

# Check template variations per user
run_test "Demestihas templates" "grep -q 'demestihas:' templates.md" "Technical templates"
run_test "Angela templates" "grep -q 'angela:' templates.md" "Friendly templates"
run_test "Children templates" "grep -q 'children:' templates.md" "Educational templates"
run_test "Neutral templates" "grep -q 'neutral:' templates.md" "Default templates"

echo ""
echo "[Phase 7] Performance Impact Test"
echo "--------------------------------"

# Test bootstrap performance hasn't degraded
echo "Running bootstrap performance test..."
BOOTSTRAP_OUTPUT=$(./test-bootstrap.sh 2>&1)
BOOTSTRAP_TIME=$(echo "$BOOTSTRAP_OUTPUT" | grep "Total Bootstrap:" | awk '{print $3}' | sed 's/ms//')

if [ -n "$BOOTSTRAP_TIME" ] && [ "$BOOTSTRAP_TIME" -lt 300 ]; then
    echo -e "Bootstrap time: ${GREEN}${BOOTSTRAP_TIME}ms${NC} (maintained < 300ms) ✓"
    PASSED_TESTS=$((PASSED_TESTS + 1))
else
    echo -e "Bootstrap time: ${RED}${BOOTSTRAP_TIME}ms${NC} (exceeds 300ms limit) ✗"
    FAILED_TESTS=$((FAILED_TESTS + 1))
fi
TOTAL_TESTS=$((TOTAL_TESTS + 1))

echo ""
echo "[Phase 8] Critical Features Test"
echo "--------------------------------"

# Check critical family features
run_test "Emergency protocols" "grep -q 'EMERGENCY_PROTOCOLS' family.md" "Safety protocols"
run_test "Notification rules" "grep -q 'NOTIFICATION_RULES' family.md" "Notifications configured"
run_test "Multi-user handling" "grep -q 'MULTI_USER_SESSION:' family.md" "Multi-user support"
run_test "Template selection" "grep -q 'SELECTION_LOGIC:' templates.md" "Dynamic selection"

echo ""
echo "==================================="
echo "Test Summary"
echo "==================================="
echo "Total Tests: $TOTAL_TESTS"
echo -e "Passed: ${GREEN}$PASSED_TESTS${NC}"
echo -e "Failed: ${RED}$FAILED_TESTS${NC}"

# Calculate pass rate
if [ $TOTAL_TESTS -gt 0 ]; then
    PASS_RATE=$((PASSED_TESTS * 100 / TOTAL_TESTS))
    echo "Pass Rate: ${PASS_RATE}%"
    
    if [ $PASS_RATE -eq 100 ]; then
        echo -e "\nStatus: ${GREEN}✅ ALL TESTS PASSED${NC}"
        EXIT_CODE=0
    elif [ $PASS_RATE -ge 90 ]; then
        echo -e "\nStatus: ${YELLOW}⚠️  MOSTLY PASSED${NC}"
        EXIT_CODE=1
    else
        echo -e "\nStatus: ${RED}❌ TESTS FAILED${NC}"
        EXIT_CODE=2
    fi
else
    echo -e "\nStatus: ${RED}❌ NO TESTS RAN${NC}"
    EXIT_CODE=3
fi

# Log results
cat >> execution.log << EOF
[$(date -u +"%Y-%m-%d %H:%M:%S UTC")] Family Context Test
  Total Tests: $TOTAL_TESTS
  Passed: $PASSED_TESTS
  Failed: $FAILED_TESTS
  Pass Rate: ${PASS_RATE}%
  Bootstrap Impact: ${BOOTSTRAP_TIME}ms
EOF

echo ""
echo "==================================="
echo "Family Context System Ready"
echo "==================================="

exit $EXIT_CODE