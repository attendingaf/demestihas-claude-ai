#!/bin/bash

# Comprehensive VPS Infrastructure Audit
# Compare actual running systems vs. intended architecture
# Date: September 1, 2025

set -e

VPS_IP="178.156.170.161"
echo "🔍 COMPREHENSIVE VPS INFRASTRUCTURE AUDIT"
echo "=========================================="
echo "Comparing actual state vs. intended multi-agent architecture"
echo ""

echo "1. RUNNING PROCESSES & SERVICES"
echo "--------------------------------"
ssh root@${VPS_IP} << 'EOF'
echo "🔍 All Python processes:"
ps aux | grep python | grep -v grep | head -20

echo -e "\n🔍 All Node.js processes:"
ps aux | grep node | grep -v grep | head -20

echo -e "\n🔍 Docker containers:"
docker ps -a | head -20

echo -e "\n🔍 Active network services (listening ports):"
netstat -tlnp | head -20

echo -e "\n🔍 SystemD services (custom):"
systemctl list-units --type=service --state=running | grep -E "(yanay|nina|lyco|huata|hermes|demestihas)" || echo "No custom systemd services found"
EOF

echo -e "\n2. FILE SYSTEM STRUCTURE"
echo "------------------------"
ssh root@${VPS_IP} << 'EOF'
echo "🔍 Root directory structure:"
ls -la /root/ | head -20

echo -e "\n🔍 Project directories in /root/:"
find /root -maxdepth 2 -type d -name "*ai*" -o -name "*agent*" -o -name "*bot*" -o -name "*yanay*" -o -name "*nina*" -o -name "*lyco*" -o -name "*huata*" -o -name "*hermes*" 2>/dev/null

echo -e "\n🔍 Contents of /root/demestihas-ai/:"
ls -la /root/demestihas-ai/ | head -20

echo -e "\n🔍 Any other Python projects:"
find /root -name "*.py" -path "*/bin" -prune -o -path "*/.local" -prune -o -print | head -30
EOF

echo -e "\n3. CONFIGURATION FILES"
echo "----------------------"
ssh root@${VPS_IP} << 'EOF'
echo "🔍 Environment files:"
find /root -name ".env*" 2>/dev/null

echo -e "\n🔍 Docker compose files:"
find /root -name "docker-compose*.yml" 2>/dev/null

echo -e "\n🔍 Service configuration files:"
find /root -name "*.service" -o -name "*.conf" -name "*demestihas*" 2>/dev/null | head -10

echo -e "\n🔍 Nginx/Apache configs (if any):"
ls -la /etc/nginx/sites-*/demestihas* /etc/apache2/sites-*/demestihas* 2>/dev/null || echo "No web server configs found"
EOF

echo -e "\n4. AGENT-SPECIFIC ANALYSIS"
echo "--------------------------"
ssh root@${VPS_IP} << 'EOF'
echo "🔍 Searching for Yanay.ai (orchestration):"
find /root -name "*yanay*" -type f 2>/dev/null | head -10
ps aux | grep -i yanay | grep -v grep || echo "No Yanay processes found"

echo -e "\n🔍 Searching for Nina (scheduler):"
find /root -name "*nina*" -type f 2>/dev/null | head -10
ps aux | grep -i nina | grep -v grep || echo "No Nina processes found"

echo -e "\n🔍 Searching for Lyco.ai (project manager):"
find /root -name "*lyco*" -type f 2>/dev/null | head -10
ps aux | grep -i lyco | grep -v grep || echo "No Lyco processes found"

echo -e "\n🔍 Searching for Huata.ai (calendar):"
find /root -name "*huata*" -type f 2>/dev/null | head -10
ps aux | grep -i huata | grep -v grep || echo "No Huata processes found"

echo -e "\n🔍 Searching for Hermes (audio):"
find /root -name "*hermes*" -type f 2>/dev/null | head -10
ps aux | grep -i hermes | grep -v grep || echo "No Hermes processes found"
docker ps | grep -i hermes || echo "No Hermes containers found"
EOF

echo -e "\n5. API INTEGRATIONS & EXTERNAL CONNECTIONS"
echo "------------------------------------------"
ssh root@${VPS_IP} << 'EOF'
echo "🔍 Active network connections:"
netstat -an | grep ESTABLISHED | head -10

echo -e "\n🔍 Webhook endpoints (if any):"
find /root -name "*.py" -exec grep -l "webhook\|/api/\|app.route" {} \; 2>/dev/null | head -10

echo -e "\n🔍 Database connections:"
ps aux | grep -E "(redis|postgres|mysql|mongo)" | grep -v grep || echo "No database processes found"

echo -e "\n🔍 Checking environment variables in active .env:"
if [ -f /root/demestihas-ai/.env ]; then
    echo "Environment variables in /root/demestihas-ai/.env:"
    grep -E "API_KEY|TOKEN|URL|_ID" /root/demestihas-ai/.env | sed 's/=.*/=***REDACTED***/'
else
    echo "No .env file found in main directory"
fi
EOF

echo -e "\n6. RESOURCE USAGE & SYSTEM HEALTH"
echo "---------------------------------"
ssh root@${VPS_IP} << 'EOF'
echo "🔍 Memory usage:"
free -h

echo -e "\n🔍 Disk usage:"
df -h | head -10

echo -e "\n🔍 CPU and load:"
uptime

echo -e "\n🔍 Recent system logs (errors):"
journalctl --since "1 hour ago" --priority=err -n 5 2>/dev/null || echo "No recent errors in journalctl"
EOF

echo -e "\n7. ARCHITECTURE MISMATCH ANALYSIS"
echo "--------------------------------"
echo "📋 Expected from diagram:"
echo "  ✓ Yanay.ai (orchestration)"  
echo "  ✓ Nina (scheduler)"
echo "  ✓ Lyco.ai (project manager)"
echo "  ✓ Huata.ai (calendar)"
echo "  ✓ Hermes (audio processing)"
echo "  ✓ Web Dashboard"
echo "  ✓ Telegram Interface"
echo "  ✓ Twilio Interface"
echo ""
echo "🔍 Analysis complete. Compare findings above with intended architecture."
echo ""
echo "❓ KEY QUESTIONS TO RESOLVE:"
echo "1. Is this a single-bot system or multi-agent system?"
echo "2. Are agents supposed to be separate processes or modules?"
echo "3. Is the diagram aspirational or current state?"
echo "4. What deployment model is intended (containers, systemd, direct Python)?"

