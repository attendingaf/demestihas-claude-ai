#!/bin/bash
# check_production_system.sh
# Script to check existing production system before deploying Eisenhower test

echo "🔍 Checking Production Multi-Agent System Status"
echo "================================================"

# SSH connection function
run_on_vps() {
    ssh root@178.156.170.161 "$1"
}

echo -e "\n📦 Docker Containers Status:"
echo "-----------------------------"
run_on_vps "docker ps --format 'table {{.Names}}\t{{.Status}}\t{{.Ports}}' | grep -E '(yanay|lyco|nina|huata|pluma|redis|telegram)' || echo 'No matching containers found'"

echo -e "\n🗂️ Project Directories:"
echo "----------------------"
run_on_vps "ls -la /root/ | grep -E '(demestihas|lyco)' || echo 'No project directories found'"

echo -e "\n📁 Multi-Agent Files:"
echo "--------------------"
run_on_vps "ls -la /root/demestihas-ai/{yanay,nina,huata,lyco_api,pluma}.py 2>/dev/null | awk '{print \$NF, \$5}' || echo 'Agent files not found'"

echo -e "\n🔗 Telegram Bot Status:"
echo "----------------------"
run_on_vps "docker logs demestihas-yanay 2>&1 | tail -5 | grep -E '(getUpdates|Telegram)' || echo 'No Telegram activity'"

echo -e "\n💾 Redis Status:"
echo "---------------"
run_on_vps "docker exec lyco-redis redis-cli ping 2>/dev/null || echo 'Redis not responding'"

echo -e "\n🌐 Network Configuration:"
echo "------------------------"
run_on_vps "docker network ls | grep lyco || echo 'No lyco network found'"

echo -e "\n⚠️ Potential Conflicts to Check:"
echo "--------------------------------"
echo "1. Container names: yanay, lyco (will use yanay-eisenhower, redis-eisenhower)"
echo "2. Telegram bot token: Using same bot would conflict"
echo "3. Redis instance: Need separate instance or namespace"
echo "4. Network: Can share lyco-network or use separate"

echo -e "\n✅ Safe Deployment Strategy:"
echo "----------------------------"
echo "• Deploy to /root/lyco-eisenhower/ (separate directory)"
echo "• Use different container names (suffix -eisenhower)"
echo "• Create test bot token (@LycurgusTestBot)"
echo "• Use isolated Redis instance"
echo "• Test thoroughly before production integration"

echo -e "\n📊 System Resources:"
echo "-------------------"
run_on_vps "df -h | grep -E '(Filesystem|/dev/)' && echo '' && free -h"

echo -e "\n🎯 Next Steps:"
echo "--------------"
echo "1. Create test bot on Telegram (@BotFather)"
echo "2. Transfer files to /root/lyco-eisenhower/"
echo "3. Configure .env with test credentials"
echo "4. Deploy with modified docker-compose.yml"
echo "5. Test without affecting production"
