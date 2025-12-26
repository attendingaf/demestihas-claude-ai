# Executive AI Mobile Platform - Product Requirements
*Integration Bridge from Claude Desktop to Mobile-First Architecture*

## Problem Statement
CMO-level physician executive with ADHD requires mobile access to AI assistant capabilities currently limited to desktop environment. Existing solutions (Claude Desktop with MCP, ChatGPT mobile) lack either custom tool integration or mobile accessibility. Need unified platform combining voice interaction, calendar management, email integration, and persistent context.

## Integration with Current System

### What We Have (Desktop)
- **Working Services**: 5/7 containers operational
- **Memory Layer**: MCP Smart Memory on port 7777
- **Calendar Agent**: Huata with OAuth (11 calendars accessible)
- **Task Management**: Lyco v2 with ADHD optimizations
- **Orchestration**: EA-AI Bridge (needs fix)
- **Architecture**: Docker containerized microservices

### What We Need (Mobile Bridge)
- **API Gateway**: Expose desktop services to mobile
- **Voice Interface**: WebRTC or Web Speech API
- **Mobile UI**: PWA or native app
- **Real-time Sync**: WebSocket connections
- **Security**: HIPAA-compliant API layer

## User Profile
* **Primary:** Healthcare executive, ADHD-hyperactive type
* **Context:** 6 calendars, complex family logistics, peak performance 9-11am
* **Constraints:** Mobile-first, voice-preferred, 15-minute task chunking required
* **Environment:** iOS primary, cross-platform needed

## Core Requirements

### P0 - Must Have
* Voice-first conversational interface
* Real-time calendar access (read/write) across 6 Google calendars
* Persistent conversation memory across sessions
* Mobile-accessible (native app or PWA)
* <30 second response time for queries
* Works offline for viewing cached data

### P1 - Should Have
* Email integration (Gmail read/draft)
* Proactive notifications (meeting warnings)
* ADHD-specific task breakdown (auto-chunk to 15min)
* Family context awareness (school schedules, au pair coordination)
* Pattern recognition for energy management

### P2 - Nice to Have
* Document search (Google Drive)
* Custom webhook/API integration
* Multi-modal input (image, document upload)
* Desktop companion app
* Team delegation features

## Technical Architecture

### VM Hosting Strategy
```
┌─────────────────────────────────────────┐
│           VM Instance                    │
│  ┌─────────────────────────────────┐    │
│  │     Current Desktop System      │    │
│  │  - Docker containers            │    │
│  │  - MCP Memory                   │    │
│  │  - Agent services               │    │
│  └──────────┬──────────────────────┘    │
│             │                            │
│  ┌──────────▼──────────────────────┐    │
│  │     API Gateway Layer           │    │
│  │  - Authentication               │    │
│  │  - Rate limiting                │    │
│  │  - WebSocket support            │    │
│  └──────────┬──────────────────────┘    │
│             │                            │
│  ┌──────────▼──────────────────────┐    │
│  │     Mobile Backend              │    │
│  │  - Voice processing             │    │
│  │  - Push notifications           │    │
│  │  - Offline sync                 │    │
│  └─────────────────────────────────┘    │
└──────────────┬──────────────────────────┘
               │
       ┌───────▼────────┐
       │   Mobile App   │
       │  (PWA/Native)  │
       └────────────────┘
```

### Integration Points with Current System

| Current Service | Mobile Interface | Priority |
|----------------|------------------|----------|
| MCP Memory (7777) | Memory API | P0 |
| Huata Calendar (8003) | Calendar API | P0 |
| Lyco Tasks (8000) | Task API | P0 |
| EA-AI Bridge (8081) | Agent Router | P1 |
| Redis Cache (6379) | Session Store | P0 |
| Mnemo (planned) | Context Manager | P1 |

## Implementation Phases

### Phase 1: API Layer (Week 1)
- Expose existing services via REST/GraphQL
- Add authentication layer
- WebSocket for real-time updates
- Deploy on VM with reverse proxy

### Phase 2: Voice Interface (Week 2)
- Integrate Whisper for STT
- Add TTS with voice selection
- WebRTC for low latency
- Voice activity detection

### Phase 3: Mobile PWA (Week 3-4)
- React/Next.js frontend
- Service worker for offline
- Push notifications
- Responsive design

### Phase 4: Native Features (Week 5-6)
- Capacitor/React Native wrapper
- Native voice integration
- Background sync
- Biometric auth

## Technical Constraints
* Must integrate with Google Workspace APIs
* Must support Claude or GPT-4 level reasoning
* Cannot require VPN or desktop tethering
* Must maintain HIPAA-compliant data handling
* Budget: <$200/month operational costs

## Stack Recommendations

### Option 1: Vercel + Supabase (Recommended)
- **Pros**: Serverless, built-in auth, real-time subscriptions
- **Integration**: Direct connection to existing containers
- **Cost**: ~$50/month
- **Time to Deploy**: 2 weeks

### Option 2: Next.js + Railway
- **Pros**: Full control, Docker native
- **Integration**: Seamless with current Docker setup
- **Cost**: ~$100/month
- **Time to Deploy**: 3 weeks

### Option 3: Bubble.io (Quick MVP)
- **Pros**: No-code, rapid deployment
- **Integration**: API connections only
- **Cost**: ~$150/month
- **Time to Deploy**: 1 week

## Success Metrics
* Time to first useful response: <5 seconds
* Calendar conflict detection rate: >95%
* Task completion rate improvement: >30%
* Daily active usage: >10 interactions
* Voice transcription accuracy: >90%

## Migration Path from Desktop

### Current Desktop Workflow
1. Open Claude Desktop
2. Use MCP tools for memory/calendar
3. Manual agent selection
4. Text-based interaction

### Future Mobile Workflow
1. "Hey Assistant" voice activation
2. Automatic context loading
3. Intelligent agent routing
4. Voice-first with visual support

## Security & Compliance
- OAuth2 for Google services
- JWT tokens with refresh
- End-to-end encryption for PHI
- HIPAA compliance via encryption at rest
- Audit logging for all accesses

## Open Questions for Technical Evaluation
1. Can existing no-code platforms (Bubble, FlutterFlow) meet P0 requirements?
2. Is WebRTC required for voice, or sufficient with Web Speech API?
3. Should memory layer use vector DB or traditional database?
4. Can single backend handle all orchestration or need microservices?
5. Is real-time calendar sync necessary or polling sufficient?

## Acceptable Trade-offs
* Web app instead of native if voice quality maintained
* 3rd party auth service vs custom implementation
* Managed services over self-hosted for non-core features
* Higher latency for complex queries if accuracy improved

## Non-Negotiable Requirements
* Must work on iPhone without desktop computer
* Must handle 6 concurrent calendar sources
* Must maintain conversation context for 30+ days
* Must support natural language time parsing ("next Tuesday at 3")
* Must protect PHI/PII in any healthcare-related queries

## Next Steps
1. Fix remaining desktop containers (EA-AI Bridge, Dashboard)
2. Implement Mnemo memory orchestration
3. Design API gateway specification
4. Create mobile UI mockups
5. Test voice integration options

---
*Created: September 23, 2025 8:52 PM EDT*
*Status: Ready for implementation planning*
