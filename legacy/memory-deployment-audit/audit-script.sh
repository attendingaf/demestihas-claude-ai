#!/bin/bash

# 1. Docker Container Status
echo "=== DOCKER CONTAINERS ===" > audit-report.txt
docker ps --format 'table {{.Names}}\t{{.Image}}\t{{.Ports}}\t{{.Status}}' >> audit-report.txt
echo "" >> audit-report.txt

# 2. Streamlit App Location & Structure
echo "=== STREAMLIT APP STRUCTURE ===" >> audit-report.txt
find /root -name "*streamlit*" -o -name "*demestichat*" -type d 2>/dev/null >> audit-report.txt
echo "" >> audit-report.txt

# 3. Current App Files
echo "=== STREAMLIT APP FILES ===" >> audit-report.txt
STREAMLIT_DIR=$(docker exec demestihas-streamlit pwd 2>/dev/null || echo "/app")
docker exec demestihas-streamlit ls -la $STREAMLIT_DIR 2>/dev/null >> audit-report.txt || echo "Could not access container" >> audit-report.txt
echo "" >> audit-report.txt

# 4. Memory API Status
echo "=== MEMORY API STATUS ===" >> audit-report.txt
curl -s http://localhost:8000/health >> audit-report.txt 2>&1
echo "" >> audit-report.txt

# 5. FalkorDB Status
echo "=== FALKORDB STATUS ===" >> audit-report.txt
docker exec demestihas-graphdb redis-cli PING >> audit-report.txt 2>&1
docker exec demestihas-graphdb redis-cli GRAPH.QUERY mene_memory "MATCH (n:Memory) RETURN count(n)" >> audit-report.txt 2>&1
echo "" >> audit-report.txt

# 6. Current Python Dependencies in Streamlit Container
echo "=== STREAMLIT PYTHON PACKAGES ===" >> audit-report.txt
docker exec demestihas-streamlit pip list 2>/dev/null | grep -E "(streamlit|requests|anthropic)" >> audit-report.txt || echo "Could not list packages" >> audit-report.txt
echo "" >> audit-report.txt

# 7. Network Configuration
echo "=== DOCKER NETWORK ===" >> audit-report.txt
docker network inspect bridge | grep -A 10 "demestihas" >> audit-report.txt 2>&1
echo "" >> audit-report.txt

# 8. JWT Token Status
echo "=== JWT TOKEN STATUS ===" >> audit-report.txt
if [ -f /root/jwt-token-only.txt ]; then
    echo "Token file exists" >> audit-report.txt
    echo "Token: $(cat /root/jwt-token-only.txt)" >> audit-report.txt
else
    echo "No token file found - will need to create" >> audit-report.txt
fi
echo "" >> audit-report.txt

# 9. Current Memory Count
echo "=== CURRENT MEMORY STATISTICS ===" >> audit-report.txt
curl -s http://localhost:8000/memory/stats 2>&1 >> audit-report.txt
echo "" >> audit-report.txt

cat audit-report.txt
