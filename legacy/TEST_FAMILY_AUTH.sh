#!/bin/bash
# Family Authentication System Test Suite
# Tests all authentication endpoints and data isolation

set -e

echo "=================================================="
echo "Family Authentication System - Test Suite"
echo "=================================================="
echo ""

API_BASE="http://agent:8000"
PASSED=0
FAILED=0

# Colors
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

function test_status() {
    if [ $1 -eq 0 ]; then
        echo -e "${GREEN}✅ PASS${NC}: $2"
        PASSED=$((PASSED + 1))
    else
        echo -e "${RED}❌ FAIL${NC}: $2"
        FAILED=$((FAILED + 1))
    fi
}

echo "Test 1: Register New User (Alice)"
echo "===================================="

RESPONSE=$(docker exec demestihas-agent curl -s -w "\n%{http_code}" -X POST \
    "$API_BASE/auth/register?user_id=alice_test&password=alice123&display_name=Alice%20Test&email=alice@test.com&role=family")
HTTP_CODE=$(echo "$RESPONSE" | tail -1)
BODY=$(echo "$RESPONSE" | head -n -1)

echo "Response: $BODY"
echo "HTTP Code: $HTTP_CODE"

if [ "$HTTP_CODE" = "200" ]; then
    test_status 0 "Alice registered successfully"
elif [ "$HTTP_CODE" = "400" ] && echo "$BODY" | grep -q "already exists"; then
    echo -e "${YELLOW}⚠️  Alice already exists (skipping)${NC}"
else
    test_status 1 "Failed to register Alice (HTTP $HTTP_CODE)"
fi

echo ""
echo "Test 2: Register Second User (Bob)"
echo "===================================="

RESPONSE=$(docker exec demestihas-agent curl -s -w "\n%{http_code}" -X POST \
    "$API_BASE/auth/register?user_id=bob_test&password=bob123&display_name=Bob%20Test&email=bob@test.com&role=family")
HTTP_CODE=$(echo "$RESPONSE" | tail -1)
BODY=$(echo "$RESPONSE" | head -n -1)

echo "Response: $BODY"
echo "HTTP Code: $HTTP_CODE"

if [ "$HTTP_CODE" = "200" ]; then
    test_status 0 "Bob registered successfully"
elif [ "$HTTP_CODE" = "400" ] && echo "$BODY" | grep -q "already exists"; then
    echo -e "${YELLOW}⚠️  Bob already exists (skipping)${NC}"
else
    test_status 1 "Failed to register Bob (HTTP $HTTP_CODE)"
fi

echo ""
echo "Test 3: Login with Valid Credentials (Alice)"
echo "=============================================="

RESPONSE=$(docker exec demestihas-agent curl -s -w "\n%{http_code}" -X POST \
    "$API_BASE/auth/login?user_id=alice_test&password=alice123")
HTTP_CODE=$(echo "$RESPONSE" | tail -1)
BODY=$(echo "$RESPONSE" | head -n -1)

echo "HTTP Code: $HTTP_CODE"

if [ "$HTTP_CODE" = "200" ]; then
    ALICE_TOKEN=$(echo "$BODY" | grep -o '"access_token":"[^"]*"' | cut -d'"' -f4)
    if [ -n "$ALICE_TOKEN" ]; then
        test_status 0 "Alice logged in successfully (token received)"
        echo "Token: ${ALICE_TOKEN:0:20}..."
    else
        test_status 1 "Login succeeded but no token received"
    fi
else
    test_status 1 "Failed to login Alice (HTTP $HTTP_CODE)"
fi

echo ""
echo "Test 4: Login with Invalid Credentials"
echo "========================================"

RESPONSE=$(docker exec demestihas-agent curl -s -w "\n%{http_code}" -X POST \
    "$API_BASE/auth/login?user_id=alice_test&password=wrongpassword")
HTTP_CODE=$(echo "$RESPONSE" | tail -1)

echo "HTTP Code: $HTTP_CODE"

if [ "$HTTP_CODE" = "401" ]; then
    test_status 0 "Invalid credentials correctly rejected"
else
    test_status 1 "Should reject invalid credentials (got HTTP $HTTP_CODE)"
fi

echo ""
echo "Test 5: Access Protected Endpoint with Token"
echo "=============================================="

if [ -n "$ALICE_TOKEN" ]; then
    RESPONSE=$(docker exec demestihas-agent curl -s -w "\n%{http_code}" \
        -H "Authorization: Bearer $ALICE_TOKEN" \
        "$API_BASE/auth/family")
    HTTP_CODE=$(echo "$RESPONSE" | tail -1)
    BODY=$(echo "$RESPONSE" | head -n -1)

    echo "HTTP Code: $HTTP_CODE"

    if [ "$HTTP_CODE" = "200" ]; then
        test_status 0 "Protected endpoint accessible with valid token"
        echo "Family members found: $(echo "$BODY" | grep -o 'alice_test\|bob_test' | wc -l)"
    else
        test_status 1 "Failed to access protected endpoint (HTTP $HTTP_CODE)"
    fi
else
    echo -e "${RED}❌ SKIP${NC}: No token available"
    FAILED=$((FAILED + 1))
fi

echo ""
echo "Test 6: Access Protected Endpoint without Token"
echo "================================================="

RESPONSE=$(docker exec demestihas-agent curl -s -w "\n%{http_code}" \
    "$API_BASE/auth/family")
HTTP_CODE=$(echo "$RESPONSE" | tail -1)

echo "HTTP Code: $HTTP_CODE"

if [ "$HTTP_CODE" = "403" ] || [ "$HTTP_CODE" = "401" ]; then
    test_status 0 "Protected endpoint correctly requires authentication"
else
    test_status 1 "Should reject request without token (got HTTP $HTTP_CODE)"
fi

echo ""
echo "Test 7: Get User Information"
echo "=============================="

if [ -n "$ALICE_TOKEN" ]; then
    RESPONSE=$(docker exec demestihas-agent curl -s -w "\n%{http_code}" \
        -H "Authorization: Bearer $ALICE_TOKEN" \
        "$API_BASE/auth/user/alice_test")
    HTTP_CODE=$(echo "$RESPONSE" | tail -1)
    BODY=$(echo "$RESPONSE" | head -n -1)

    echo "HTTP Code: $HTTP_CODE"

    if [ "$HTTP_CODE" = "200" ] && echo "$BODY" | grep -q "Alice Test"; then
        test_status 0 "User information retrieved successfully"
        echo "Display name: $(echo "$BODY" | grep -o '"display_name":"[^"]*"' | cut -d'"' -f4)"
    else
        test_status 1 "Failed to get user information (HTTP $HTTP_CODE)"
    fi
else
    echo -e "${RED}❌ SKIP${NC}: No token available"
    FAILED=$((FAILED + 1))
fi

echo ""
echo "Test 8: Verify Database Storage"
echo "================================="

USER_COUNT=$(docker exec demestihas-postgres psql -U mene_demestihas -d demestihas_db -t -c \
    "SELECT COUNT(*) FROM users WHERE id IN ('alice_test', 'bob_test');" 2>/dev/null | tr -d ' ')

echo "Test users in database: $USER_COUNT"

if [ "$USER_COUNT" -ge 1 ]; then
    test_status 0 "Users stored in PostgreSQL database"
else
    test_status 1 "Users not found in database"
fi

echo ""
echo "Test 9: Verify Password Hash Storage"
echo "======================================"

HAS_HASH=$(docker exec demestihas-postgres psql -U mene_demestihas -d demestihas_db -t -c \
    "SELECT COUNT(*) FROM users WHERE id='alice_test' AND password_hash IS NOT NULL AND password_hash != '';" 2>/dev/null | tr -d ' ')

echo "Password hash present: $HAS_HASH"

if [ "$HAS_HASH" = "1" ]; then
    test_status 0 "Password hash stored (not plaintext)"

    # Verify it's actually hashed (starts with $2b$ for bcrypt)
    HASH_PREFIX=$(docker exec demestihas-postgres psql -U mene_demestihas -d demestihas_db -t -c \
        "SELECT substring(password_hash from 1 for 4) FROM users WHERE id='alice_test';" 2>/dev/null | tr -d ' ')

    if [ "$HASH_PREFIX" = "\$2b\$" ] || [ "$HASH_PREFIX" = "\$2a\$" ]; then
        test_status 0 "Password properly hashed with bcrypt"
    else
        test_status 1 "Password hash format incorrect (not bcrypt)"
    fi
else
    test_status 1 "Password hash not stored"
fi

echo ""
echo "Test 10: Backend Compatibility (Deprecated Endpoint)"
echo "======================================================"

RESPONSE=$(docker exec demestihas-agent curl -s -w "\n%{http_code}" -X POST \
    "$API_BASE/auth/token?user_id=alice_test")
HTTP_CODE=$(echo "$RESPONSE" | tail -1)

echo "HTTP Code: $HTTP_CODE"

if [ "$HTTP_CODE" = "200" ]; then
    test_status 0 "Backward compatibility endpoint still works"
    echo -e "${YELLOW}⚠️  Warning: This endpoint is deprecated and insecure${NC}"
else
    test_status 1 "Backward compatibility endpoint broken (HTTP $HTTP_CODE)"
fi

echo ""
echo "=================================================="
echo "Test Summary"
echo "=================================================="
echo ""
TOTAL=$((PASSED + FAILED))
echo "Total Tests: $TOTAL"
echo -e "${GREEN}Passed: $PASSED${NC}"
echo -e "${RED}Failed: $FAILED${NC}"
echo ""

if [ $FAILED -eq 0 ]; then
    echo -e "${GREEN}✅ All tests passed! Family authentication system is working.${NC}"
    exit 0
else
    echo -e "${RED}❌ Some tests failed. Please review the errors above.${NC}"
    exit 1
fi
