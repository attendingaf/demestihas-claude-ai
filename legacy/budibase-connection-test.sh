#!/bin/bash
# Budibase Connection Pre-Test Script
# Run this BEFORE configuring Budibase to verify database is accessible

echo "======================================"
echo "DispoAssist V0 - Connection Test"
echo "======================================"
echo ""

# Colors for output
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo "Testing connection to Supabase database..."
echo ""

# Test 1: Basic connection
echo -n "Test 1: Basic Connection... "
PGPASSWORD="DispoAssist2025!SecureDB" psql \
  "postgresql://postgres@db.wklxknnhgbnyragemqoy.supabase.co:5432/postgres?sslmode=require" \
  -c "SELECT 1;" -t -A > /dev/null 2>&1

if [ $? -eq 0 ]; then
    echo -e "${GREEN}✅ PASSED${NC}"
else
    echo -e "${RED}❌ FAILED${NC}"
    echo "Cannot connect to database. Check credentials and network."
    exit 1
fi

# Test 2: List tables
echo -n "Test 2: Fetch Tables... "
TABLES=$(PGPASSWORD="DispoAssist2025!SecureDB" psql \
  "postgresql://postgres@db.wklxknnhgbnyragemqoy.supabase.co:5432/postgres?sslmode=require" \
  -t -A -c "SELECT table_name FROM information_schema.tables WHERE table_schema='public' AND table_name IN ('calls','barriers','tasks','medications','appointments') ORDER BY table_name;")

TABLE_COUNT=$(echo "$TABLES" | wc -l)

if [ "$TABLE_COUNT" -eq 5 ]; then
    echo -e "${GREEN}✅ PASSED (5 tables found)${NC}"
else
    echo -e "${RED}❌ FAILED (expected 5, found $TABLE_COUNT)${NC}"
    exit 1
fi

# Test 3: List each table
echo ""
echo "Tables detected:"
echo "$TABLES" | while read table; do
    echo "  - $table"
done

# Test 4: Row counts
echo ""
echo -n "Test 3: Check Table Access... "
PGPASSWORD="DispoAssist2025!SecureDB" psql \
  "postgresql://postgres@db.wklxknnhgbnyragemqoy.supabase.co:5432/postgres?sslmode=require" \
  -t -A -c "
SELECT
    'calls: ' || COUNT(*) || ' rows' FROM calls
    UNION ALL
    SELECT 'barriers: ' || COUNT(*) || ' rows' FROM barriers
    UNION ALL
    SELECT 'tasks: ' || COUNT(*) || ' rows' FROM tasks
    UNION ALL
    SELECT 'medications: ' || COUNT(*) || ' rows' FROM medications
    UNION ALL
    SELECT 'appointments: ' || COUNT(*) || ' rows' FROM appointments;
" > /tmp/row_counts.txt 2>&1

if [ $? -eq 0 ]; then
    echo -e "${GREEN}✅ PASSED${NC}"
    echo ""
    echo "Current row counts:"
    cat /tmp/row_counts.txt | while read line; do
        echo "  $line"
    done
else
    echo -e "${RED}❌ FAILED${NC}"
    exit 1
fi

# Test 5: RLS Check
echo ""
echo -n "Test 4: RLS Status... "
RLS_COUNT=$(PGPASSWORD="DispoAssist2025!SecureDB" psql \
  "postgresql://postgres@db.wklxknnhgbnyragemqoy.supabase.co:5432/postgres?sslmode=require" \
  -t -A -c "SELECT COUNT(*) FROM pg_tables WHERE schemaname='public' AND rowsecurity=true AND tablename IN ('calls','barriers','tasks','medications','appointments');")

if [ "$RLS_COUNT" -eq 5 ]; then
    echo -e "${GREEN}✅ PASSED (RLS enabled on all tables)${NC}"
else
    echo -e "${YELLOW}⚠️  WARNING (RLS not enabled on all tables)${NC}"
fi

echo ""
echo "======================================"
echo -e "${GREEN}All connection tests passed!${NC}"
echo "======================================"
echo ""
echo "You can now proceed with Budibase configuration."
echo ""
echo "Connection details for Budibase:"
echo "  Host: db.wklxknnhgbnyragemqoy.supabase.co"
echo "  Port: 5432"
echo "  Database: postgres"
echo "  User: postgres"
echo "  Password: DispoAssist2025!SecureDB"
echo "  SSL: Required ✅"
echo ""
