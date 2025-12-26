# Phase 4 Requirements: Learning & Optimization

## User Story
**As a Lyco user**, I want the system to learn from my behavior patterns and operate autonomously with instant response times, **so that** I never have to think about the system itself, only my tasks.

## Acceptance Criteria
- [ ] Skip patterns analyzed and used to improve task generation
- [ ] Response time consistently under 1 second
- [ ] Weekly insights email generated with actionable recommendations  
- [ ] System operates for 48 hours without manual intervention
- [ ] UI polished with smooth transitions and keyboard shortcuts

## Technical Specification

### 1. Adaptive Intelligence System
**File**: `src/adaptive_intelligence.py`

```python
class AdaptiveIntelligence:
    def analyze_skip_patterns(self, days_back=30):
        """
        Query skip_patterns table to identify:
        - Tasks skipped >3 times with same pattern
        - Energy mismatches (wrong-time skips)  
        - Context failures (need-someone/missing-context)
        - False positives (not-important skips)
        """
        
    def generate_prompt_adjustments(self, insights):
        """
        Create LLM prompt modifications:
        - Adjust energy classification rules
        - Refine task extraction criteria
        - Update context detection logic
        - Modify confidence thresholds
        """
        
    def update_processor_prompts(self, adjustments):
        """
        Apply to processor.py with version tracking
        Store in prompt_versions table
        Track performance metrics
        """
```

### 2. Performance Optimization
**File**: `src/performance_optimizer.py`

Key optimizations:
- Redis caching for next task queue (pre-fetch top 5)
- Composite database indexes
- Background processing for pattern analysis
- Query result caching with 5-minute TTL

**Database Migration**: `migrations/phase4_optimization.sql`
```sql
CREATE INDEX idx_tasks_next_fetch 
ON tasks(completed_at, skipped_at, energy_level, created_at) 
WHERE completed_at IS NULL AND skipped_at IS NULL;

CREATE MATERIALIZED VIEW daily_metrics AS
SELECT 
    DATE(created_at) as date,
    COUNT(*) FILTER (WHERE completed_at IS NOT NULL) as completed,
    COUNT(*) FILTER (WHERE skipped_at IS NOT NULL) as skipped
FROM tasks
GROUP BY DATE(created_at);
```

### 3. Weekly Insights Generator
**File**: `src/weekly_insights.py`

Generates HTML email with:
- Productivity metrics (completion rate, peak hours)
- Behavioral patterns discovered
- System learning updates
- Actionable recommendations
- Visual charts using HTML/CSS

Only sends if:
- User had >10 tasks this week
- Significant patterns detected
- Improvements to highlight

### 4. System Health Monitor  
**File**: `src/health_monitor.py`

Monitors every 5 minutes:
- Database connectivity
- Redis availability
- LLM API responsiveness
- Queue depths
- Error rates

Self-healing actions:
- Restart stalled processors
- Clear blocked queues  
- Fallback to cached responses
- Alert if manual intervention needed

### 5. UI Polish
**Update**: `static/index.html`

Enhancements:
- Smooth fade/slide transitions
- Keyboard shortcuts (Enter=done, S=skip)
- Daily progress indicator
- Contextual loading messages
- Celebration message variations

## Test Plan

### Unit Tests (`test_phase4.py`)
1. **Adaptive Intelligence**
   - Create mock skip patterns
   - Verify prompt adjustments generated
   - Measure improvement metrics

2. **Performance**
   - Verify <1 second response time
   - Test cache hit rates >70%
   - Validate query optimization

3. **Insights**
   - Generate sample weekly data
   - Verify email formatting
   - Test relevance filtering

4. **Autonomous Operation**
   - Run for 48 hours
   - Monitor self-healing triggers
   - Verify no manual intervention

### Integration Tests
1. End-to-end flow with caching
2. Pattern learning with real data
3. Weekly insights with actual metrics
4. Health monitoring with simulated failures

### User Acceptance Tests
1. Observe skip rate reduction over 1 week
2. Verify insights provide value
3. Confirm zero system thinking required
4. Validate autonomous operation

## Technical Approach

### Architecture Changes
```
┌─────────────┐     ┌──────────────┐
│   Browser   │────▶│  Server.py   │
└─────────────┘     └──────┬───────┘
                           │
                    ┌──────▼───────┐
                    │ Redis Cache  │
                    └──────┬───────┘
                           │
         ┌─────────────────┼─────────────────┐
         │                 │                 │
    ┌────▼────┐    ┌───────▼──────┐   ┌─────▼────┐
    │Adaptive │    │Performance   │   │ Health   │
    │ Intel   │    │Optimizer     │   │ Monitor  │
    └────┬────┘    └───────┬──────┘   └─────┬────┘
         │                 │                 │
         └─────────────────┼─────────────────┘
                           │
                    ┌──────▼───────┐
                    │   Supabase   │
                    └──────────────┘
```

### Data Flow
1. User requests task → Check Redis cache
2. Cache miss → Query optimized database
3. Background: Analyze patterns every 5 min
4. Background: Update prompts based on learning
5. Weekly: Generate and send insights
6. Continuous: Monitor health and self-heal

### Error Handling
- LLM failures: Fallback to cached responses
- Database issues: Retry with exponential backoff
- Redis down: Direct database queries
- Pattern analysis failure: Log and continue

## Dependencies
- Existing: Redis, Supabase, Anthropic SDK
- New: None (using existing infrastructure)

## Deployment Steps
1. Apply database migration
2. Deploy new Python modules
3. Update server.py with integrations
4. Deploy updated HTML
5. Run validation suite
6. Monitor for 48 hours

## Success Metrics
- **Primary**: 20% skip rate reduction
- **Performance**: <1 second response time
- **Accuracy**: 80%+ energy matching
- **Reliability**: 48-hour autonomous operation
- **Value**: 90%+ find insights valuable

## Ready for Implementation ✅
This specification is complete and ready to paste into Claude Code for Phase 4 implementation.