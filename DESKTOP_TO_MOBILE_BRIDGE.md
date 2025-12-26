# Desktop to Mobile Bridge Specification
*Connecting Claude Desktop Beta to Mobile Platform*

## Current System → Mobile Platform Bridge

### 🎯 Executive Summary
Transform your working Claude Desktop system into a mobile-accessible AI assistant by:
1. Exposing existing Docker services via API Gateway
2. Adding voice interface layer
3. Building progressive web app
4. Maintaining all current functionality

### 📊 System Readiness Assessment

| Component | Desktop Status | Mobile Ready? | Required Changes |
|-----------|---------------|---------------|------------------|
| MCP Memory | ✅ Working | ✅ Yes | Add REST API wrapper |
| Huata Calendar | ✅ Working | ✅ Yes | Already has API |
| Lyco Tasks | ✅ Working | ✅ Yes | Already has API |
| EA-AI Bridge | ❌ Needs fix | ⏸️ Blocked | Fix health checks first |
| Redis Cache | ✅ Working | ✅ Yes | Use for sessions |
| Mnemo | 📝 Planned | 🔄 Ready | Implement first |

### 🏗️ Architecture Bridge

```
┌─────────────────────────────────────────────────┐
│              CURRENT (Desktop)                   │
├─────────────────────────────────────────────────┤
│  Claude Desktop → MCP Tools → Docker Services   │
│                                                  │
│  - Local execution                              │
│  - Direct tool access                           │
│  - No authentication                            │
└─────────────────────────────────────────────────┘
                      ↓
┌─────────────────────────────────────────────────┐
│             BRIDGE (API Gateway)                 │
├─────────────────────────────────────────────────┤
│  Mobile App → API Gateway → Docker Services     │
│                                                  │
│  - JWT authentication                           │
│  - REST/GraphQL endpoints                       │
│  - WebSocket for real-time                      │
│  - Rate limiting & caching                      │
└─────────────────────────────────────────────────┘
                      ↓
┌─────────────────────────────────────────────────┐
│              TARGET (Mobile)                     │
├─────────────────────────────────────────────────┤
│  Voice → AI → Agents → Response → Voice         │
│                                                  │
│  - Voice-first interaction                      │
│  - Background sync                              │
│  - Push notifications                           │
│  - Offline capabilities                         │
└─────────────────────────────────────────────────┘
```

## Implementation Steps

### Step 1: Fix Current System (Days 1-2)
```bash
# Fix EA-AI Bridge
docker exec -it demestihas-ea-ai-bridge sh
# Debug and fix health endpoint

# Implement Mnemo
cd /Projects/demestihas-ai
# Run Claude Code with REQUIREMENTS.md

# Verify all healthy
curl http://localhost:8081/health
curl http://localhost:8004/health
```

### Step 2: Create API Gateway (Days 3-5)
```javascript
// gateway/index.js
import express from 'express';
import jwt from 'jsonwebtoken';
import proxy from 'http-proxy-middleware';

const app = express();

// Authentication middleware
app.use('/api', authenticateToken);

// Service proxies
const services = {
  '/api/memory': 'http://demestihas-mcp-memory:7777',
  '/api/calendar': 'http://demestihas-huata:8003',
  '/api/tasks': 'http://demestihas-lyco-v2:8000',
  '/api/agents': 'http://demestihas-ea-ai-bridge:8081'
};

// Route to services
Object.entries(services).forEach(([path, target]) => {
  app.use(path, proxy({ 
    target, 
    changeOrigin: true,
    ws: true // WebSocket support
  }));
});

app.listen(3000, () => {
  console.log('API Gateway running on port 3000');
});
```

### Step 3: Add Voice Layer (Days 6-7)
```javascript
// voice/processor.js
import { Whisper } from '@openai/whisper';
import { ElevenLabs } from 'elevenlabs';

export class VoiceProcessor {
  async speechToText(audioBuffer) {
    const text = await whisper.transcribe(audioBuffer);
    return text;
  }
  
  async textToSpeech(text) {
    const audio = await elevenLabs.synthesize(text, {
      voice: 'executive-assistant',
      speed: 1.1 // ADHD-friendly faster pace
    });
    return audio;
  }
}
```

### Step 4: Mobile PWA (Days 8-14)
```typescript
// mobile-app/pages/index.tsx
import { useVoiceAssistant } from '../hooks/useVoiceAssistant';
import { useWebSocket } from '../hooks/useWebSocket';

export default function AssistantApp() {
  const { isListening, startListening, stopListening } = useVoiceAssistant();
  const { messages, sendMessage } = useWebSocket();
  
  return (
    <div className="assistant-interface">
      <VoiceButton 
        onPress={isListening ? stopListening : startListening}
        isActive={isListening}
      />
      <MessageDisplay messages={messages} />
      <QuickActions>
        <ActionButton onClick={() => sendMessage('Check calendar conflicts')} />
        <ActionButton onClick={() => sendMessage('What should I focus on?')} />
        <ActionButton onClick={() => sendMessage('Summarize emails')} />
      </QuickActions>
    </div>
  );
}
```

## VM Deployment Configuration

### Docker Compose Addition
```yaml
# Add to docker-compose.yml
api-gateway:
  container_name: demestihas-api-gateway
  build: ./gateway
  ports:
    - "3000:3000"
    - "3001:3001"
  environment:
    - NODE_ENV=production
    - JWT_SECRET=${JWT_SECRET}
    - REDIS_URL=redis://demestihas-redis:6379
  networks:
    - demestihas-network
  depends_on:
    - redis
    - mcp-memory
    - huata
    - lyco-v2
    - ea-ai-bridge
  restart: unless-stopped

voice-processor:
  container_name: demestihas-voice
  build: ./voice
  ports:
    - "3002:3002"
  environment:
    - WHISPER_API_KEY=${WHISPER_API_KEY}
    - ELEVENLABS_API_KEY=${ELEVENLABS_API_KEY}
  networks:
    - demestihas-network
  restart: unless-stopped
```

### Nginx Configuration for VM
```nginx
# /etc/nginx/sites-available/demestihas-ai
server {
  listen 443 ssl http2;
  server_name ai.demestihas.com;
  
  ssl_certificate /etc/letsencrypt/live/ai.demestihas.com/fullchain.pem;
  ssl_certificate_key /etc/letsencrypt/live/ai.demestihas.com/privkey.pem;
  
  # API Gateway
  location /api/ {
    proxy_pass http://localhost:3000/;
    proxy_http_version 1.1;
    proxy_set_header Upgrade $http_upgrade;
    proxy_set_header Connection 'upgrade';
  }
  
  # WebSocket
  location /ws/ {
    proxy_pass http://localhost:3001/;
    proxy_http_version 1.1;
    proxy_set_header Upgrade $http_upgrade;
    proxy_set_header Connection 'upgrade';
  }
  
  # Mobile App (if serving from same domain)
  location / {
    proxy_pass http://localhost:3003/;
  }
}
```

## Testing Strategy

### Desktop Functionality Preservation
```bash
# Ensure all desktop features still work
claude-desktop --test-tools
curl http://localhost:7777/health
curl http://localhost:8003/health
```

### Mobile API Testing
```bash
# Test API Gateway
curl https://ai.demestihas.com/api/memory/health
curl https://ai.demestihas.com/api/calendar/health

# Test voice endpoint
curl -X POST https://ai.demestihas.com/api/voice/transcribe \
  -F "audio=@test.wav"

# Test WebSocket
wscat -c wss://ai.demestihas.com/ws/
```

## Rollout Plan

### Week 1: Foundation
- [ ] Fix EA-AI Bridge
- [ ] Implement Mnemo
- [ ] Deploy API Gateway
- [ ] Test all endpoints

### Week 2: Voice
- [ ] Integrate Whisper API
- [ ] Add TTS service
- [ ] Test latency (<2s)
- [ ] Voice activity detection

### Week 3-4: Mobile UI
- [ ] PWA scaffolding
- [ ] Authentication flow
- [ ] Core screens
- [ ] Offline mode

### Week 5-6: Polish
- [ ] Push notifications
- [ ] Background sync
- [ ] Performance optimization
- [ ] User testing

## Success Criteria
- [ ] All desktop tools accessible via API
- [ ] Voice response <5 seconds
- [ ] Mobile app works offline
- [ ] Calendar conflicts detected
- [ ] ADHD task chunking works
- [ ] Family context preserved

## Budget Impact
| Component | Monthly Cost |
|-----------|-------------|
| VM hosting (current) | $50 |
| Vercel (frontend) | $20 |
| Whisper API | $10 |
| ElevenLabs TTS | $5 |
| Push notifications | $5 |
| **Total Additional** | **$40** |

## Risk Mitigation
1. **Desktop breaks**: All changes additive, not modifying core
2. **Latency issues**: Cache aggressively, optimize queries
3. **Security concerns**: JWT + HTTPS + rate limiting
4. **Cost overrun**: Monitor usage, set alerts at 80%

---
*Created: September 23, 2025 8:53 PM EDT*
*Ready for Implementation*
