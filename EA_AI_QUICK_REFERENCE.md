# EA-AI Quick Reference Card

## 🤖 Agent Roles & Responsibilities

**PLUMA - Email Intelligence**
- Email drafting, searching, and management
- Gmail integration and inbox operations

**HUATA - Calendar Orchestration**  
- Calendar management and conflict resolution
- Meeting scheduling across 6 calendars
- Event and availability checks

**LYCO - Task & Time Management** 
- ALL task breakdown and prioritization
- Time management and scheduling
- ADHD optimizations (15-min chunks, energy matching)
- Deadline tracking and temporal awareness
- "When is my next meeting?" queries
- Finding free time in schedule

**KAIROS - Networking & Professional Development**
- LinkedIn and professional communications
- Career coaching and development
- Administrative support tasks
- Professional relationship management
- Meeting prep for networking events
- Contact management and CRM functions

## 🚀 Setup Status
- [ ] Run: `./setup-simplified.sh`
- [ ] Restart Claude Desktop
- [ ] Test EA-AI tools

## 🛠 EA-AI Tools in Claude

### 1. Memory Operations
```
ea_ai_memory get session_state
ea_ai_memory set [key] [value]
ea_ai_memory search [pattern]
ea_ai_memory persist
```

### 2. Agent Routing
```
ea_ai_route pluma [email operation]
ea_ai_route huata [calendar operation]
ea_ai_route lyco [task/time management operation]
ea_ai_route kairos [networking/professional operation]
ea_ai_route auto [any operation]
```

### 3. Family Context
```
ea_ai_family mene preferences
ea_ai_family cindy schedule
ea_ai_family auto current
```

### 4. Calendar Check (6 calendars)
```
ea_ai_calendar_check check_conflicts
ea_ai_calendar_check find_free_time
ea_ai_calendar_check next_event
```

### 5. ADHD Task Management
```
ea_ai_task_adhd break_down [task]
ea_ai_task_adhd prioritize [task]
ea_ai_task_adhd time_block [task]
ea_ai_task_adhd energy_match [task]
```

## 📅 Calendar IDs
```
menelaos4@gmail.com                                    # Primary
mene@beltlineconsulting.co                            # Work
7dia35946hir6rbq10stda8hk4@group.calendar.google.com  # LyS Familia
e46i6ac3ipii8b7iugsqfeh2j8@group.calendar.google.com  # Limon y Sal
c4djl5q698b556jqliablah9uk@group.calendar.google.com  # Cindy
up5jrbrsng5le7qmu0uhi6pedo@group.calendar.google.com  # Au Pair
```

## 💬 Test Commands for Claude

**Basic Tests:**
- "Use EA-AI to check my calendar for conflicts"
- "EA-AI: Break this task into 15-minute chunks: prepare Q4 presentation"
- "Route through EA-AI: draft email declining meeting invitation"
- "EA-AI memory: remember I prefer morning meetings 9-11am"

**Advanced Tests:**
- "EA-AI: What's my energy level and next task?"
- "Use Pluma to search for emails about the budget"
- "Huata: Find free time across all calendars tomorrow"
- "Lyco: When is my next meeting and what free time do I have?"
- "Lyco: Break down this complex project into 15-minute chunks"
- "Kairos: Draft a LinkedIn message for professional introduction"
- "Kairos: Help me with networking prep for tomorrow's event"

## 🔧 Troubleshooting

**If EA-AI tools don't work:**
1. Check Claude Desktop is fully restarted
2. Verify config: `cat ~/Library/Application\ Support/Claude/claude_desktop_config.json | grep ea-ai`
3. Test bootstrap: `node ~/Projects/claude-desktop-ea-ai/test-integration.js`
4. Monitor: `~/Projects/claude-desktop-ea-ai/monitor-ea-ai.sh`

**If memory isn't persisting:**
- Use: `ea_ai_memory persist` after important updates
- Check: `ea_ai_memory get session_state` at start

**If calendar conflicts missed:**
- Always use `ea_ai_calendar_check check_conflicts` first
- Then `list_gcal_events` for details

## 📊 Performance Targets
- Bootstrap: <300ms ✓
- Memory operations: <50ms
- Agent routing: <100ms
- Cache hit rate: >80%

## 🎯 Key Behaviors
- **15-minute chunks** for all tasks (ADHD)
- **N-dashes** for summaries (never bullets)
- **"Why This Works"** before email drafts
- **Trade-offs** for all decisions
- **Live calendar** checks (never static)
- **Pattern storage** after 3 occurrences
- **Energy matching** for task scheduling

## 🏠 Family Dynamics
- **Eight + Six**: Balance confidence with reassurance
- **ADHD considerations**: Visual reminders, written follow-ups
- **Morning energy**: 9-11am for complex work
- **School schedule**: 8am-3:30pm weekdays
- **Family time**: Dinner 6:30pm, bedtime 8:30pm

## 📝 Files Created
```
/Projects/claude-desktop-ea-ai/
├── bootstrap.js              # Core EA-AI system
├── mcp-server-simple.js      # MCP bridge
├── setup-simplified.sh       # Setup script
├── CLAUDE_INSTRUCTIONS_EA_AI.md  # Full instructions
├── CUSTOM_INSTRUCTIONS_SHORT.md  # For Claude settings
├── state.md                  # Session state
├── routing.md                # Agent routing matrix
├── cache.md                  # Cache configuration
├── smart-memory.md           # Memory patterns
├── family.md                 # Family context
└── templates.md              # Response templates
```

## ✅ Success Indicators
- Claude remembers context between sessions
- Tasks automatically break into 15-min chunks
- Calendar conflicts detected across all 6
- Family preferences applied automatically
- Bootstrap completes in <300ms
- Patterns improve interactions over time

---
*Keep this reference handy while using EA-AI Enhanced Claude Desktop*
