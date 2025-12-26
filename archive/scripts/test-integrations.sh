#!/bin/bash

# Tool Integration Test Suite
# Tests tool-specific routing, calendar IDs, and handler functionality

echo "========================================="
echo "Claude Desktop Family AI"
echo "Tool Integration Test Suite (Phase 5)"
echo "========================================="
echo ""

# Color codes
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

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

echo "[Phase 1] Tool Configuration Files"
echo "--------------------------------"

# Check config files exist
run_test "tool_bindings.md exists" "[ -f config/tool_bindings.md ]" "Config file should exist"
run_test "calendar_ids.md exists" "[ -f config/calendar_ids.md ]" "Calendar registry should exist"

# Check integration handlers
run_test "pluma_handler.md exists" "[ -f integrations/pluma_handler.md ]" "Email handler should exist"
run_test "huata_handler.md exists" "[ -f integrations/huata_handler.md ]" "Calendar handler should exist"
run_test "lyco_handler.md exists" "[ -f integrations/lyco_handler.md ]" "Task handler should exist"
run_test "kairos_handler.md exists" "[ -f integrations/kairos_handler.md ]" "Time handler should exist"

echo ""
echo "[Phase 2] Tool Routing Matrix"
echo "--------------------------------"

# Check tool definitions
run_test "Pluma defined" "grep -q 'pluma:' config/tool_bindings.md" "Email tool configured"
run_test "Huata defined" "grep -q 'huata:' config/tool_bindings.md" "Calendar tool configured"
run_test "Lyco defined" "grep -q 'lyco:' config/tool_bindings.md" "Task tool configured"
run_test "Kairos defined" "grep -q 'kairos:' config/tool_bindings.md" "Time tool configured"

# Check mandatory routing
run_test "Mandatory routing" "grep -q 'MANDATORY' config/tool_bindings.md" "Mandatory flag set"
run_test "No fallback rule" "grep -q 'NO fallback to generic' config/tool_bindings.md" "Strict routing enforced"

echo ""
echo "[Phase 3] Calendar ID Configuration"
echo "--------------------------------"

# Check all 6 calendars
run_test "LyS Familia calendar" "grep -q '7dia35946hir6rbq10stda8hk4' config/calendar_ids.md" "Family calendar ID"
run_test "Beltline calendar" "grep -q 'mene@beltlineconsulting.co' config/calendar_ids.md" "Work calendar ID"
run_test "Primary calendar" "grep -q 'menelaos4@gmail.com' config/calendar_ids.md" "Personal calendar ID"
run_test "Limon y Sal calendar" "grep -q 'e46i6ac3ipii8b7iugsqfeh2j8' config/calendar_ids.md" "Restaurant calendar ID"
run_test "Cindy calendar" "grep -q 'c4djl5q698b556jqliablah9uk' config/calendar_ids.md" "Cindy's calendar ID"
run_test "Au Pair calendar" "grep -q 'up5jrbrsng5le7qmu0uhi6pedo' config/calendar_ids.md" "Au Pair calendar ID"

# Check calendar routing rules
run_test "Calendar selection rules" "grep -q 'CALENDAR_SELECTION:' config/calendar_ids.md" "Selection logic defined"
run_test "Conflict resolution" "grep -q 'CONFLICT' config/calendar_ids.md" "Conflict handling defined"
run_test "15-minute blocks" "grep -q '15_minutes' config/calendar_ids.md" "Time blocking configured"

echo ""
echo "[Phase 4] Handler Integration"
echo "--------------------------------"

# Check handler trigger patterns
run_test "Email triggers" "grep -q 'EMAIL_TRIGGERS:' integrations/pluma_handler.md" "Email patterns defined"
run_test "Calendar triggers" "grep -q 'CALENDAR_TRIGGERS:' integrations/huata_handler.md" "Calendar patterns defined"
run_test "Task triggers" "grep -q 'TASK_TRIGGERS:' integrations/lyco_handler.md" "Task patterns defined"
run_test "Networking triggers" "grep -q 'NETWORKING_TRIGGERS:' integrations/kairos_handler.md" "Networking patterns defined"

# Check ADHD support (now in Lyco)
run_test "ADHD patterns in Lyco" "grep -q 'ADHD' integrations/lyco_handler.md" "ADHD support in task manager"
run_test "LinkedIn in Kairos" "grep -q 'LinkedIn' integrations/kairos_handler.md" "LinkedIn integration in networking"

# Check cache integration
run_test "Pluma cache strategy" "grep -q 'cache_strategy:' integrations/pluma_handler.md" "Email caching defined"
run_test "Huata real-time" "grep -q 'real_time' integrations/huata_handler.md" "Calendar real-time mode"

echo ""
echo "[Phase 5] Routing Enhancement"
echo "--------------------------------"

# Check routing.md updates
run_test "Tool-specific routing added" "grep -q 'TOOL-SPECIFIC ROUTING' routing.md" "Phase 5 routing added"
run_test "Pluma routing" "grep -q 'PLUMA_HANDLER' routing.md" "Email routing configured"
run_test "Huata routing" "grep -q 'HUATA_HANDLER' routing.md" "Calendar routing configured"
run_test "Lyco routing" "grep -q 'LYCO_HANDLER' routing.md" "Task routing configured"
run_test "Kairos routing" "grep -q 'KAIROS_HANDLER' routing.md" "Time routing configured"
run_test "Tool check first" "grep -q 'Tool-specific check happens FIRST' routing.md" "Priority ordering correct"

echo ""
echo "[Phase 6] Performance Impact"
echo "--------------------------------"

# Test bootstrap performance still good
echo "Running bootstrap test..."
BOOTSTRAP_OUTPUT=$(./test-bootstrap.sh 2>&1)
BOOTSTRAP_TIME=$(echo "$BOOTSTRAP_OUTPUT" | grep "Total Bootstrap:" | awk '{print $3}' | sed 's/ms//')

if [ -n "$BOOTSTRAP_TIME" ] && [ "$BOOTSTRAP_TIME" -lt 300 ]; then
    echo -e "Bootstrap time: ${GREEN}${BOOTSTRAP_TIME}ms${NC} (maintained < 300ms) ✓"
    PASSED_TESTS=$((PASSED_TESTS + 1))
else
    echo -e "Bootstrap time: ${RED}${BOOTSTRAP_TIME}ms${NC} (exceeds 300ms) ✗"
    FAILED_TESTS=$((FAILED_TESTS + 1))
fi
TOTAL_TESTS=$((TOTAL_TESTS + 1))

echo ""
echo "[Phase 7] Fallback Behavior"
echo "--------------------------------"

# Check fallback strategies
run_test "Pluma fallback" "grep -q 'when_pluma_unavailable:' integrations/pluma_handler.md" "Email fallback defined"
run_test "Huata fallback" "grep -q 'calendar_unreachable:' integrations/huata_handler.md" "Calendar fallback defined"
run_test "Circuit breaker" "grep -q 'circuit_break' config/tool_bindings.md" "Circuit breaker configured"

echo ""
echo "[Phase 8] Logging Enhancement"
echo "--------------------------------"

# Check logging formats
run_test "Tool logging format" "grep -q 'TOOL|' routing.md" "Tool decisions logged"
run_test "Calendar logging" "grep -q 'HUATA|' integrations/huata_handler.md" "Calendar ops logged"
run_test "Email logging" "grep -q 'PLUMA|' integrations/pluma_handler.md" "Email ops logged"

echo ""
echo "========================================="
echo "Test Summary"
echo "========================================="
echo "Total Tests: $TOTAL_TESTS"
echo -e "Passed: ${GREEN}$PASSED_TESTS${NC}"
echo -e "Failed: ${RED}$FAILED_TESTS${NC}"

# Calculate pass rate
if [ $TOTAL_TESTS -gt 0 ]; then
    PASS_RATE=$((PASSED_TESTS * 100 / TOTAL_TESTS))
    echo "Pass Rate: ${PASS_RATE}%"
    
    if [ $PASS_RATE -eq 100 ]; then
        echo -e "\nStatus: ${GREEN}✅ ALL INTEGRATION TESTS PASSED${NC}"
        echo "Tool-specific routing is fully operational"
        EXIT_CODE=0
    elif [ $PASS_RATE -ge 90 ]; then
        echo -e "\nStatus: ${YELLOW}⚠️  MOSTLY PASSED${NC}"
        echo "Minor issues in tool integration"
        EXIT_CODE=1
    else
        echo -e "\nStatus: ${RED}❌ INTEGRATION TESTS FAILED${NC}"
        echo "Tool routing needs attention"
        EXIT_CODE=2
    fi
else
    echo -e "\nStatus: ${RED}❌ NO TESTS RAN${NC}"
    EXIT_CODE=3
fi

# Log results
cat >> execution.log << EOF
[$(date -u +"%Y-%m-%d %H:%M:%S UTC")] Integration Test (Phase 5)
  Total Tests: $TOTAL_TESTS
  Passed: $PASSED_TESTS
  Failed: $FAILED_TESTS
  Pass Rate: ${PASS_RATE}%
  Bootstrap Time: ${BOOTSTRAP_TIME}ms
EOF

echo ""
echo "========================================="
echo "Tool Integration System Ready"
echo "========================================="

exit $EXIT_CODE