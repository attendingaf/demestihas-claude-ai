#!/usr/bin/env python3
"""
Hermes Email Container Diagnostic Script
Generates diagnostic commands for VPS troubleshooting
"""

diagnostic_commands = """
# Hermes Email Container Network Diagnostic
# Execute these commands on VPS (SSH root@178.156.170.161)

echo "=== Docker Network Analysis ==="
docker network ls

echo "=== Network Configuration ==="
docker inspect lyco-ai_default

echo "=== Container Status Check ==="
docker ps -a | grep hermes

echo "=== Current Compose Services ==="
cd /root/lyco-ai
docker-compose ps

echo "=== Container Logs (if exists) ==="
docker logs hermes_audio_container --tail 20 2>/dev/null || echo "No hermes container found"

echo "=== Docker Compose Configuration Check ==="
grep -A 10 -B 2 "hermes_audio" docker-compose.yml || echo "No hermes_audio service found"
"""

print("Hermes Email Container Diagnostic")
print("=" * 50)
print(diagnostic_commands)
print("\nDiagnostic commands ready for VPS execution")
