#!/usr/bin/env python3
"""
Hermes Email Container Fix Script
Prepares corrected docker-compose.yml configuration
"""

# Corrected hermes_audio service configuration from handoff
hermes_service_yaml = """
  hermes_audio:
    build:
      context: ./hermes_audio
      dockerfile: Dockerfile
    container_name: hermes_audio_container
    environment:
      - HERMES_EMAIL_ADDRESS=hermesaudio444@gmail.com
      - HERMES_EMAIL_PASSWORD=${HERMES_EMAIL_PASSWORD}
      - EMAIL_IMAP_SERVER=imap.gmail.com
      - ANTHROPIC_API_KEY=${ANTHROPIC_API_KEY}
      - OPENAI_API_KEY=${OPENAI_API_KEY}
      - LYCO_API_URL=http://bot:8000
    volumes:
      - ./hermes_audio:/app
      - ./logs:/app/logs
    networks:
      - default
    restart: unless-stopped
    depends_on:
      - bot
"""

fix_commands = """
# Hermes Email Container Network Fix Commands
# Execute these commands on VPS (SSH root@178.156.170.161)

echo "=== Stopping conflicting containers ==="
docker stop $(docker ps -aq --filter name=hermes) 2>/dev/null || true
docker rm $(docker ps -aq --filter name=hermes) 2>/dev/null || true

echo "=== Creating backup ==="
cd /root/lyco-ai
cp docker-compose.yml docker-compose.yml.backup

echo "=== Edit docker-compose.yml to add/fix hermes_audio service ==="
# Use nano or vim to add the service configuration above
# IMPORTANT: Add explicit 'networks: - default' and 'depends_on: - bot'

echo "=== Rebuild hermes_audio service ==="
docker-compose build hermes_audio

echo "=== Start hermes_audio service ==="
docker-compose up -d hermes_audio

echo "=== Verify container status ==="
docker ps | grep hermes
docker logs hermes_audio_container --tail 50
"""

print("Hermes Email Container Fix")
print("=" * 40)
print("SERVICE CONFIGURATION TO ADD:")
print(hermes_service_yaml)
print("\nFIX COMMANDS:")
print(fix_commands)

# Write the service configuration for easy copying
with open("~/Projects/demestihas-ai/hermes_service_config.yml", "w") as f:
    f.write(hermes_service_yaml)

print("\nService config saved to: ~/Projects/demestihas-ai/hermes_service_config.yml")
print("Ready for VPS deployment")
