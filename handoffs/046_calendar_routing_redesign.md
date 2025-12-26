# Handoff #046: Calendar Routing Architecture Redesign

**Thread Type**: PM-Opus Strategic Design
**Priority**: MEDIUM - After system stabilization  
**Duration**: Design phase only (implementation separate)
**Context**: Calendar routing broke task routing, needs architectural solution

## Strategic Problem Analysis

### What Happened
1. Calendar intent checking was added BEFORE task routing
2. Calendar detection intercepted ALL messages first
3. Many queries matched calendar keywords but needed task handling
4. Result: Task queries got misrouted → 400 errors → system failure

### Root Cause
**Serial Processing Pipeline** where calendar hijacked the flow:
```
Message → Calendar Check → (If match) → Calendar Handler ❌
                         ↘ (If no match) → Task Handler
```

Problem: Calendar keywords too broad, overlap with task language

### Architecture Solution

## New Parallel Intent Architecture

Instead of serial checking, implement **parallel intent scoring**:

```
Message → Intent Analyzer → Score All Intents → Route to Highest Score
           ↓
    ┌──────┴──────┬──────────┬────────┐
    ↓             ↓          ↓        ↓
Calendar(0.3)  Task(0.8)  Schedule  Health
                  ↓         (0.1)    (0.0)
                Winner
                  ↓
              Task Handler
```

## Implementation Design

### 1. Intent Scoring System

```python
class IntentScorer:
    """
    Score each intent independently, route to highest confidence
    """
    
    def score_calendar_intent(self, message: str) -> float:
        """
        Score 0.0 to 1.0 for calendar likelihood
        """
        score = 0.0
        
        # Strong calendar indicators (+0.3 each)
        strong_calendar = ['calendar', 'schedule', 'appointment', 'meeting']
        for word in strong_calendar:
            if word in message.lower():
                score += 0.3
        
        # Temporal questions (+0.2 each)
        temporal = ['when am i', 'am i free', 'what time', "what's on my"]
        for phrase in temporal:
            if phrase in message.lower():
                score += 0.2
        
        # Day references with calendar context (+0.1)
        if any(day in message.lower() for day in ['monday','tuesday','wednesday','thursday','friday','saturday','sunday']):
            if 'free' in message.lower() or 'busy' in message.lower():
                score += 0.2
        
        # Negative indicators (-0.3 each)
        task_words = ['create task', 'add task', 'remind me to', 'need to']
        for phrase in task_words:
            if phrase in message.lower():
                score -= 0.3
        
        return min(max(score, 0.0), 1.0)  # Clamp to 0-1
    
    def score_task_intent(self, message: str) -> float:
        """
        Score 0.0 to 1.0 for task likelihood
        """
        score = 0.0
        
        # Strong task indicators (+0.4 each)
        task_verbs = ['create', 'add', 'make', 'remind', 'need to', 'have to', 'should']
        for verb in task_verbs:
            if verb in message.lower():
                score += 0.4
        
        # Task query indicators (+0.5)
        if 'show my tasks' in message.lower() or 'what tasks' in message.lower():
            score += 0.5
        
        # Task object words (+0.2)
        if 'task' in message.lower() or 'todo' in message.lower():
            score += 0.2
        
        # Urgency indicators (+0.2)
        if any(word in message.lower() for word in ['urgent', 'important', 'asap', 'priority']):
            score += 0.2
        
        return min(max(score, 0.0), 1.0)
    
    def score_schedule_intent(self, message: str) -> float:
        """Score for Nina's au pair scheduling"""
        score = 0.0
        
        if 'viola' in message.lower():
            score += 0.5
        if any(word in message.lower() for word in ['coverage', 'babysitter', 'childcare']):
            score += 0.3
        if 'schedule' in message.lower() and 'viola' in message.lower():
            score += 0.2
            
        return min(max(score, 0.0), 1.0)
    
    def route_message(self, message: str) -> Tuple[str, float]:
        """
        Return (handler_name, confidence_score)
        """
        scores = {
            'task': self.score_task_intent(message),
            'calendar': self.score_calendar_intent(message),
            'schedule': self.score_schedule_intent(message),
        }
        
        # Get highest scoring intent
        best_intent = max(scores.items(), key=lambda x: x[1])
        
        # Default to task if no strong signal
        if best_intent[1] < 0.2:
            return ('task', 0.5)  # Default fallback
            
        return best_intent
```

### 2. Graceful Fallback System

```python
class RouterWithFallback:
    """
    If primary handler fails, try secondary
    """
    
    async def route_with_fallback(self, message: str, user_id: str):
        # Get primary and secondary intents
        scorer = IntentScorer()
        scores = {
            'task': scorer.score_task_intent(message),
            'calendar': scorer.score_calendar_intent(message),
            'schedule': scorer.score_schedule_intent(message),
        }
        
        # Sort by score
        sorted_intents = sorted(scores.items(), key=lambda x: x[1], reverse=True)
        primary = sorted_intents[0]
        secondary = sorted_intents[1] if len(sorted_intents) > 1 else None
        
        # Try primary handler
        try:
            if primary[0] == 'calendar':
                result = await self.handle_calendar(message, user_id)
            elif primary[0] == 'task':
                result = await self.handle_task(message, user_id)
            elif primary[0] == 'schedule':
                result = await self.handle_schedule(message, user_id)
                
            # If result is error-ish, try secondary
            if 'error' in str(result).lower() or '400' in str(result):
                if secondary and secondary[1] > 0.3:
                    logger.info(f"Primary {primary[0]} failed, trying {secondary[0]}")
                    # Recursive call with secondary
                    return await self.route_to_handler(secondary[0], message, user_id)
                    
            return result
            
        except Exception as e:
            logger.error(f"Handler {primary[0]} failed: {e}")
            if secondary and secondary[1] > 0.3:
                return await self.route_to_handler(secondary[0], message, user_id)
            raise
```

### 3. Handler Response Validation

Each handler must return structured response indicating success/failure:

```python
@dataclass
class HandlerResponse:
    success: bool
    confidence: float  # How confident the handler was
    response: str      # User-facing message
    should_fallback: bool  # Explicitly request fallback
    metadata: Dict[str, Any]  # Additional context
```

### 4. Integration Points

**Yanay Changes Required**:
1. Replace serial intent checking with parallel scoring
2. Add fallback mechanism
3. Log all routing decisions for analysis
4. Implement gradual rollout with feature flag

**Testing Strategy**:
1. Run BOTH old and new routing in parallel
2. Log when they disagree
3. Manually review disagreements
4. Gradually increase new router percentage

## Migration Plan

### Phase 1: Shadow Mode (Week 1)
- Implement new router alongside old
- Log all decisions but don't act on them
- Analyze logs for accuracy

### Phase 2: Canary Deployment (Week 2)
- 10% of messages use new router
- Monitor for errors
- Gradual increase to 50%

### Phase 3: Full Rollout (Week 3)
- 100% on new router
- Old router code removed
- Monitoring continues

## Success Metrics

1. **Zero Task Routing Failures**: "show my tasks" always works
2. **95% Calendar Accuracy**: Calendar queries route correctly
3. **Graceful Degradation**: Fallback prevents 400 errors
4. **Performance**: <50ms additional latency for scoring
5. **Observability**: Complete routing decision trail in logs

## Risk Mitigation

1. **Feature Flag Control**:
```python
if ENABLE_PARALLEL_ROUTING:
    result = parallel_router.route(message)
else:
    result = serial_router.route(message)  # Current approach
```

2. **Circuit Breaker**:
If error rate exceeds 10%, automatically revert to serial routing

3. **A/B Testing**:
Route specific users to new system first (start with Mene)

## Architecture Benefits

1. **Non-Destructive**: Adding new agents doesn't break existing ones
2. **Explainable**: Can show why routing decision was made
3. **Learnable**: Can adjust scores based on feedback
4. **Extensible**: Easy to add new agents/intents
5. **Testable**: Each scorer can be unit tested independently

## Next Implementation Steps

1. Create `intent_scorer.py` with scoring logic
2. Create test suite with 100+ example messages
3. Implement shadow mode in Yanay
4. Deploy and collect 24 hours of logs
5. Analyze and tune scoring weights
6. Begin canary deployment

## Documentation Requirements

Must document:
- Scoring algorithm and weights
- How to add new intent types
- How to debug routing decisions
- Performance impact measurements
- Rollback procedures

This architecture ensures calendar features can be added WITHOUT breaking core task management functionality.
