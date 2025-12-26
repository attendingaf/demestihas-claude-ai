# THREAD: Developer Thread #023 - Hermes Email Docker Network Fix
**ATOMIC SCOPE**: Fix Hermes email container network configuration to enable email-to-task processing

## CONTEXT
- **Current State**: Hermes container defined but fails to start due to docker network issues
- **Diagnostic Result**: Thread #021 found network unreachable errors preventing container startup
- **Files to Modify**: `/root/lyco-ai/docker-compose.yml` on VPS
- **Dependencies**: Existing Gmail credentials (hermesaudio444@gmail.com) configured in .env
- **Expected Duration**: 30 minutes maximum

## IMPLEMENTATION

### Step 1: Diagnose Docker Network Issue
```bash
# SSH to VPS
ssh root@178.156.170.161

# Check current container status
docker ps -a | grep hermes

# Check docker-compose logs for specific error
docker-compose logs hermes_audio
```

### Step 2: Fix Network Configuration
Likely issues to check:
1. **Network reference**: Ensure hermes_audio service uses correct network
2. **Port conflicts**: Verify no port conflicts with existing containers
3. **Service definition**: Validate YAML syntax in docker-compose.yml

Expected fix pattern:
```yaml
services:
  hermes_audio:
    build:
      context: ./hermes_audio
    networks:
      - default  # Use same network as other services
    environment:
      - HERMES_EMAIL_ADDRESS=${HERMES_EMAIL_ADDRESS}
      - HERMES_EMAIL_PASSWORD=${HERMES_EMAIL_PASSWORD}
      - LYCO_API_URL=http://bot:8000  # Correct container reference
```

### Step 3: Start and Validate Container
```bash
# Rebuild and start
docker-compose up -d --build hermes_audio

# Verify running
docker ps | grep hermes_audio

# Check logs for successful startup
docker logs $(docker ps -q -f name=hermes_audio) --tail 20
```

## SUCCESS TEST
```bash
# Container should show as running
docker ps | grep hermes_audio | grep "Up"

# Logs should show email monitoring started
docker logs $(docker ps -q -f name=hermes_audio) | grep -i "monitoring\|email\|started"

# No network errors in logs
docker logs $(docker ps -q -f name=hermes_audio) | grep -i error
```

## ROLLBACK PLAN
- If breaks existing containers: `docker-compose down && docker-compose up -d`
- If hermes_audio won't start: Comment out hermes_audio service in docker-compose.yml
- If complete system failure: Revert to backup docker-compose.yml

## REPORTING
- **Update current_state.md section**: Audio Processing System - Hermes Email status
- **Add thread_log.md entry**: Thread #023 outcome with specific fix applied
- **Document**: Exact network configuration solution for future reference

## FAMILY COMMUNICATION AFTER SUCCESS
**Family Update**: Email Audio Processing  
**Who Benefits**: Everyone  
**What Changed**: Can now email audio files to hermesaudio444@gmail.com for automatic task extraction  
**How to Use**: Record voice memo → Email to hermesaudio444@gmail.com → Tasks appear in Notion automatically  
**If Problems**: Use batch processor (`./process_audio.sh`) as backup method  

**Expected Outcome**: Family has two working audio processing methods within 30 minutes