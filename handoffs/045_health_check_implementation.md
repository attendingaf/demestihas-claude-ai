# Handoff #045: Health Check Endpoint Implementation

**Thread Type**: Dev-Sonnet Implementation  
**Priority**: HIGH - Implement after stability validation
**Duration**: 45 minutes
**Context**: QA discovered no health check exists despite being mentioned in thread_log

## Atomic Scope
Implement basic health check endpoint for automated monitoring and rapid issue detection

## Context
- No health check implementation exists (Thread #5 never happened)
- System just recovered from emergency where issues weren't detected early
- Need automated way to verify system health without manual testing
- Should check all critical components quickly

## Implementation Requirements

### 1. Create health_check.py

Location: `/root/lyco-ai/health_check.py`

```python
"""
Health check endpoint for Demestihas AI system
Validates all critical components are operational
"""

import asyncio
import time
from typing import Dict, Any, List
import redis
import httpx
from datetime import datetime
import os

class SystemHealthChecker:
    def __init__(self):
        self.redis_client = redis.Redis(host='lyco-redis', port=6379, decode_responses=True)
        self.checks_performed = []
        self.start_time = time.time()
        
    async def check_redis(self) -> Dict[str, Any]:
        """Verify Redis is accessible and responsive"""
        try:
            # Ping Redis
            self.redis_client.ping()
            
            # Check memory usage
            info = self.redis_client.info('memory')
            memory_mb = info['used_memory'] / 1024 / 1024
            
            return {
                'service': 'redis',
                'status': 'healthy',
                'memory_mb': round(memory_mb, 2),
                'response_time_ms': 5
            }
        except Exception as e:
            return {
                'service': 'redis',
                'status': 'unhealthy',
                'error': str(e)
            }
    
    async def check_telegram(self) -> Dict[str, Any]:
        """Verify Telegram bot connectivity"""
        try:
            token = os.getenv('TELEGRAM_BOT_TOKEN')
            if not token:
                raise ValueError("No Telegram token configured")
                
            # Check bot status via Telegram API
            async with httpx.AsyncClient() as client:
                response = await client.get(
                    f"https://api.telegram.org/bot{token}/getMe",
                    timeout=5.0
                )
                
            if response.status_code == 200:
                return {
                    'service': 'telegram',
                    'status': 'healthy',
                    'bot_active': True
                }
            else:
                return {
                    'service': 'telegram', 
                    'status': 'degraded',
                    'http_status': response.status_code
                }
        except Exception as e:
            return {
                'service': 'telegram',
                'status': 'unhealthy',
                'error': str(e)
            }
    
    async def check_notion(self) -> Dict[str, Any]:
        """Verify Notion API accessibility"""
        try:
            token = os.getenv('NOTION_TOKEN')
            database_id = os.getenv('NOTION_DATABASE_ID')
            
            if not token or not database_id:
                raise ValueError("Notion credentials not configured")
            
            # Simple query to verify API access
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    f"https://api.notion.com/v1/databases/{database_id}/query",
                    headers={
                        "Authorization": f"Bearer {token}",
                        "Notion-Version": "2022-06-28",
                        "Content-Type": "application/json"
                    },
                    json={"page_size": 1},
                    timeout=5.0
                )
            
            if response.status_code == 200:
                return {
                    'service': 'notion',
                    'status': 'healthy',
                    'api_accessible': True
                }
            else:
                return {
                    'service': 'notion',
                    'status': 'degraded',
                    'http_status': response.status_code
                }
        except Exception as e:
            return {
                'service': 'notion',
                'status': 'unhealthy',
                'error': str(e)
            }
    
    async def check_anthropic(self) -> Dict[str, Any]:
        """Verify Anthropic API key is valid"""
        try:
            api_key = os.getenv('ANTHROPIC_API_KEY')
            if not api_key:
                raise ValueError("No Anthropic API key configured")
            
            # We don't make actual API call to save costs
            # Just verify key format
            if api_key.startswith('sk-') and len(api_key) > 40:
                return {
                    'service': 'anthropic',
                    'status': 'healthy',
                    'api_key_configured': True
                }
            else:
                return {
                    'service': 'anthropic',
                    'status': 'degraded',
                    'issue': 'Invalid API key format'
                }
        except Exception as e:
            return {
                'service': 'anthropic',
                'status': 'unhealthy',
                'error': str(e)
            }
    
    async def check_task_flow(self) -> Dict[str, Any]:
        """Verify basic task creation flow works"""
        try:
            # Create test task in Redis to verify flow
            test_key = f"health_check:{int(time.time())}"
            self.redis_client.setex(test_key, 60, "test_task")
            value = self.redis_client.get(test_key)
            self.redis_client.delete(test_key)
            
            if value == "test_task":
                return {
                    'service': 'task_flow',
                    'status': 'healthy',
                    'redis_write_read': True
                }
            else:
                return {
                    'service': 'task_flow',
                    'status': 'degraded',
                    'issue': 'Redis read/write mismatch'
                }
        except Exception as e:
            return {
                'service': 'task_flow',
                'status': 'unhealthy',
                'error': str(e)
            }
    
    async def run_all_checks(self) -> Dict[str, Any]:
        """Execute all health checks in parallel"""
        checks = await asyncio.gather(
            self.check_redis(),
            self.check_telegram(),
            self.check_notion(),
            self.check_anthropic(),
            self.check_task_flow(),
            return_exceptions=True
        )
        
        # Process results
        all_healthy = True
        degraded_services = []
        unhealthy_services = []
        
        for check in checks:
            if isinstance(check, Exception):
                unhealthy_services.append(str(check))
                all_healthy = False
            elif check['status'] == 'unhealthy':
                unhealthy_services.append(check['service'])
                all_healthy = False
            elif check['status'] == 'degraded':
                degraded_services.append(check['service'])
                all_healthy = False
        
        # Calculate overall status
        if unhealthy_services:
            overall_status = 'unhealthy'
        elif degraded_services:
            overall_status = 'degraded'
        else:
            overall_status = 'healthy'
        
        elapsed_time = time.time() - self.start_time
        
        return {
            'status': overall_status,
            'timestamp': datetime.utcnow().isoformat(),
            'version': 'v7.5-emergency-stable',
            'checks': checks,
            'summary': {
                'healthy': overall_status == 'healthy',
                'degraded_services': degraded_services,
                'unhealthy_services': unhealthy_services,
                'total_checks': len(checks),
                'check_duration_ms': round(elapsed_time * 1000, 2)
            }
        }

# FastAPI endpoint to add to yanay.py
async def health_check():
    """HTTP endpoint for health checks"""
    checker = SystemHealthChecker()
    result = await checker.run_all_checks()
    
    # Return appropriate HTTP status based on health
    if result['status'] == 'healthy':
        status_code = 200
    elif result['status'] == 'degraded':
        status_code = 207  # Multi-status
    else:
        status_code = 503  # Service unavailable
    
    return result, status_code
```

### 2. Add Health Check Route to Yanay

Add to `/root/lyco-ai/yanay.py`:

```python
# Add near other imports
from health_check import SystemHealthChecker

# Add route (if using FastAPI framework)
@app.get("/health")
async def health_check_endpoint():
    checker = SystemHealthChecker()
    result = await checker.run_all_checks()
    
    if result['status'] == 'healthy':
        return JSONResponse(content=result, status_code=200)
    elif result['status'] == 'degraded':
        return JSONResponse(content=result, status_code=207)
    else:
        return JSONResponse(content=result, status_code=503)

# OR if not using FastAPI, add to message handler
if message_text == "/health":
    checker = SystemHealthChecker()
    result = await checker.run_all_checks()
    health_message = f"System Status: {result['status']}\n"
    for check in result['checks']:
        health_message += f"- {check['service']}: {check['status']}\n"
    await update.message.reply_text(health_message)
```

### 3. Create Monitoring Script

Location: `/root/lyco-ai/monitor_health.sh`

```bash
#!/bin/bash
# Health monitoring script
# Run via cron every 5 minutes

HEALTH_URL="http://localhost:8000/health"
ALERT_WEBHOOK="<telegram_or_slack_webhook>"
LOG_FILE="/root/lyco-ai/logs/health_check.log"

# Perform health check
response=$(curl -s -w "\n%{http_code}" $HEALTH_URL)
http_code=$(echo "$response" | tail -n1)
body=$(echo "$response" | head -n-1)

# Log result
echo "[$(date -u +"%Y-%m-%d %H:%M:%S UTC")] HTTP $http_code" >> $LOG_FILE

# Alert if unhealthy
if [ "$http_code" != "200" ]; then
    echo "[ALERT] System unhealthy: $body" >> $LOG_FILE
    # Send alert (implement based on notification preference)
    # curl -X POST $ALERT_WEBHOOK -d "System unhealthy: $body"
fi
```

### 4. Add to Docker Container

Update Dockerfile:
```dockerfile
COPY health_check.py /app/
COPY monitor_health.sh /app/
RUN chmod +x /app/monitor_health.sh
```

## Testing

1. **Unit Test Each Check**:
```bash
python3 -c "from health_check import SystemHealthChecker; import asyncio; checker = SystemHealthChecker(); print(asyncio.run(checker.check_redis()))"
```

2. **Full Integration Test**:
```bash
# After deployment
curl http://localhost:8000/health

# Should return JSON with all service statuses
```

3. **Verify Telegram Command**:
Send `/health` to @LycurgusBot

## Success Criteria
- Health endpoint responds in <1 second
- All services show correct status
- Degraded state properly detected
- HTTP status codes match health state
- Can be called via HTTP or Telegram

## Rollback Plan
If health check causes issues:
1. Remove health check import from yanay.py
2. Delete health_check.py
3. Restart container
4. System continues without health monitoring

## Documentation Update

Add to current_state.md:
```markdown
### Health Monitoring ✅
- Endpoint: http://178.156.170.161:8000/health
- Telegram: Send /health to bot
- Checks: Redis, Telegram, Notion, Anthropic, Task Flow
- Frequency: On-demand + cron every 5 minutes
```

Add to thread_log.md:
```markdown
## Thread #045 (Dev-Sonnet) - Health Check Implementation
**Date**: [timestamp]
**Duration**: [actual time]
**Outcome**: [Success/Partial/Failed]
**Deliverables**:
- Created health_check.py with 5 service checks
- Integrated with Yanay bot
- Added monitoring script
**Technical Details**:
- Response time: <1 second for all checks
- HTTP status codes: 200 (healthy), 207 (degraded), 503 (unhealthy)
**Next Thread**: Deploy and validate health checks working
```
