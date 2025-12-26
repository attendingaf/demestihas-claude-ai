# Demestihas.ai Beta - Quick Start Guide

## What This Is
A Claude Desktop Project that simulates the entire Demestihas.ai multi-agent system locally for testing and learning. It's self-aware and documents insights to improve the production VPS deployment.

## How to Start Testing

### 1. Create New Claude Desktop Project
- Name: "Demestihas.ai Beta"
- Instructions: Copy contents of `BETA_PROJECT_INSTRUCTIONS.md`

### 2. Test Basic Commands

#### Simple Task Creation
"I need to buy milk tomorrow"
*Expected: Lyco extracts task, assigns priority, confirms*

#### Context Reference  
"Actually make that urgent"
*Expected: Yanay resolves "that" to previous task*

#### Schedule Management
"Nina works 6am to 9am and 2pm to 9pm on weekdays"
*Expected: Nina parses split shift correctly*

#### Calendar Query
"Am I free Thursday afternoon?"
*Expected: Huata checks availability (simulated)*

#### Multi-Agent Request
"Schedule a meeting with John when we're both free"
*Expected: Huata checks calendar, Lyco creates task*

### 3. Watch for Learning Opportunities

The system should:
- Notice when responses feel unnatural
- Document confusion points
- Track repeated corrections
- Identify missing capabilities
- Record family-specific patterns

### 4. Check Documentation Updates

After each session, verify updates to:
- `learnings_log.md` - New insights added
- `beta_state.md` - Capabilities updated
- `interaction_history.md` - Session summarized
- `vps_recommendations.md` - Production improvements queued

## Testing Personas

### As Mene (Primary)
- ADHD Type: Hyperactive
- Style: Direct, action-oriented
- Test: Quick task capture, energy-based scheduling

### As Cindy
- ADHD Type: Inattentive  
- Style: Needs visual organization
- Test: Family coordination, gentle reminders

### As Kids
- Persy (11): Multi-step tasks
- Stelios (8): Simple clear tasks
- Franci (5): Single-step with emojis

### As Viola (Au Pair)
- Style: Needs clear instructions
- Test: Schedule clarity, task handoffs

## Key Metrics to Track

### Quantitative
- Task extraction accuracy (target: 85%)
- Response time (target: <2s perceived)
- Corrections needed per session
- Multi-agent handoff success rate

### Qualitative  
- Cognitive load (feels overwhelming?)
- Natural flow (conversation or commands?)
- Trust level (would you rely on it?)
- Family readiness (ready for others?)

## Common Test Flows

### Morning Planning
1. "What do I need to do today?"
2. "What's urgent?"
3. "How much time do I need?"
4. "Am I free at 2pm?"
5. "Move the 2pm to tomorrow"

### Task Dump
1. "I need to call dentist, buy groceries, review proposal, and pickup kids"
2. "The proposal is urgent"
3. "Groceries can wait until weekend"
4. "Kids pickup is at 3pm"

### Family Coordination
1. "What does Viola's schedule look like this week?"
2. "Can she cover Thursday evening?"
3. "Add family dinner to Saturday"
4. "Remind kids about chores"

## Debug Commands

### Check System State
"Show me your current capabilities"
*Should list what's working/not working*

### Force Documentation
"What did you learn from that interaction?"
*Should trigger learning log update*

### Test Specific Agent
"As Lyco, extract tasks from: [message]"
*Should respond as specific agent*

### Review Patterns
"What patterns have you noticed about my requests?"
*Should summarize learned preferences*

## Red Flags to Document

If you see these, immediately document in learnings_log:
- Response takes >3 seconds
- System misunderstands basic request
- Context lost between messages
- Wrong agent responds
- Task extraction fails on simple sentence
- Family member confusion
- ADHD overwhelm triggered

## Success Indicators

You know it's working when:
- Feels like talking to a helpful assistant
- Tasks extracted without corrections
- References understood naturally
- Multiple agents coordinate smoothly
- Responses are concise but complete
- You'd trust family members to use it

---

**Remember:** This beta is learning from you. Every interaction makes the production system better for your family.
