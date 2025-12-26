# Beta Demestihas AI Multi-Agent System
**Primary Development Environment for Claude Desktop**

## Strategic Framework
**Development Philosophy**: Test locally in Claude Desktop → Deploy proven functionality to VPS
- **Beta Environment**: Claude Desktop EA (full functionality testing)
- **Production VPS**: Minimal deployment (proven features only)

## Agent Development Priorities

### Phase 1: Core Multi-Agent System (Current)
1. **Yanay Surrogate** - Meta-orchestrator for Claude Desktop
   - Route messages to appropriate agents
   - Context management across agents
   - Integration with Claude Desktop functions

2. **Lyco Integration** - Task management (lessons from VPS)
   - Eisenhower matrix management
   - Task parsing with Claude Haiku
   - Daily/weekly task review

### Phase 2: Email & Calendar Agents
3. **Pluma** - Email management and executive assistant
   - Gmail integration and OAuth setup
   - Email drafting with tone learning
   - Smart inbox management
   - Meeting notes processing

4. **Huata** - Calendar management
   - Google Calendar integration
   - Event scheduling and coordination
   - Calendar-based task planning

5. **Nina** - Scheduling and coordination
   - Au pair coordination
   - Family scheduling
   - German language support for Viola

### Phase 3: Advanced Intelligence Agents
6. **Mnemo** - Cutting-edge memory management
   - Short-term: Working memory and context
   - Medium-term: Session and project memory
   - Long-term: Knowledge graph and pattern recognition
   - Memory compression and retrieval optimization

7. **Sophia** - Executive coaching agent
   - **Core Teachings Integration**:
     - Crucial Conversations (Patrick Lencioni)
     - Charisma Myth (Olivia Fox Cabane)  
     - Five Dysfunctions (Patrick Lencioni)
     - Strengths Based Leadership (Tom Rath)
     - Radical Candor (Kim Scott)
     - Let Them Theory (Mel Robbins)
     - First 90 Days (Michael Watkins)
     - Power (Jeffrey Pfeffer)
   - Situational coaching recommendations
   - Leadership development tracking
   - Team dynamics analysis

## Development Environment

### Local Testing (Claude Desktop)
```
claude-desktop-ea-ai/
├── agents/
│   ├── yanay/          # Meta-orchestrator
│   ├── lyco/           # Task management
│   ├── pluma/          # Email agent
│   ├── huata/          # Calendar agent
│   ├── nina/           # Scheduling agent
│   ├── mnemo/          # Memory management
│   └── sophia/         # Executive coaching
├── shared/
│   ├── memory/         # Cross-agent memory
│   ├── coaching/       # Executive coaching content
│   └── utils/          # Common utilities
├── tests/              # Agent testing
└── deployment/         # VPS graduation configs
```

### VPS Deployment (Minimal)
```
demestihas-ai/
├── lyco_api.py         # Eisenhower matrix bot
├── yanay.py           # Simple orchestration
├── docker-compose.yml # Container deployment
└── .env               # VPS configuration
```

## Family Context Integration

### User Specialization
- **Mene**: Lyco (task management), Sophia (executive coaching), Mnemo (memory)
- **Cindy**: Nina (ER scheduling), Huata (calendar coordination)
- **Viola**: Nina (au pair coordination), German language support
- **Kids**: Age-appropriate task and scheduling assistance

### Agent Communication Patterns
```
Claude Desktop → Yanay Surrogate → Agent Selection → Tool Usage → Response
```

## Success Criteria

### Beta Testing (Claude Desktop)
- ✅ All agents accessible through Claude Desktop functions
- ✅ Cross-agent context sharing working
- ✅ Family members can test specific agent capabilities
- ✅ Memory and coaching agents providing value

### VPS Graduation
- ✅ Lyco Eisenhower matrix fully functional
- ✅ Telegram bot responsive and reliable
- ✅ Task parsing and daily review working
- ✅ Family adoption of core functionality

## Development Approach

### Local-First Development
1. **Build in Claude Desktop**: Full functionality testing
2. **Family Beta Testing**: Real-world validation
3. **Performance Optimization**: Memory and response time tuning
4. **VPS Preparation**: Containerization and deployment configs
5. **Graduated Deployment**: Move proven features to VPS

### Quality Gates
- **Functionality**: Works reliably in Claude Desktop
- **Performance**: Fast response times for family use
- **Integration**: Smooth inter-agent communication
- **Value**: Measurable improvement in productivity/coaching

## Current Status

### Immediate Focus
1. **Clean up project structure** ✅
2. **Set up Claude Desktop agent framework**
3. **Integrate VPS Lyco lessons**
4. **Build Yanay surrogate for orchestration**

### Next Milestones
- [ ] Beta Demestihas MAS framework functional
- [ ] Lyco integration working locally
- [ ] Pluma email functionality tested
- [ ] Memory and coaching agents providing value
- [ ] VPS deployment of proven Lyco functionality

---

**Development Environment**: `~/Projects/claude-desktop-ea-ai/`
**VPS Deployment**: `~/Projects/demestihas-ai/` → `root@178.156.170.161:/root/demestihas-ai/`
**Backup**: All original work preserved in `~/Projects/backup-20240904/`