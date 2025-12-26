# Lyco 2.0 System State

## Current Status: Phase 3 Complete ✅
**Last Updated**: December 15, 2024  
**Environment**: Local Development  
**Next Phase**: Phase 4 - Learning & Optimization

---

## What's Working Today

### Core Pipeline ✅
- **Signal Capture**: Manual signals via CLI working
- **LLM Processing**: Claude Opus extracting tasks with 90% accuracy  
- **Task Surfacing**: Single next task based on energy level
- **Web Interface**: Clean single-task view at `localhost:8000`

### Skip Intelligence ✅
- **Smart Actions**: Skip reasons trigger automatic behaviors
  - `wrong-time/low-energy` → Auto-reschedules
  - `need-someone/missing-context` → Creates delegation signals
  - `not-now/no-time` → Parks for weekly review
  - `not-important` → Soft deletes with pattern learning
- **Pattern Learning**: Detects repeated skip behaviors after 3 occurrences
- **Weekly Review**: Email generated for parked tasks

### Database Schema ✅
```sql
-- Core tables
task_signals         -- Raw capture from reality
tasks               -- Processed actionable items
skip_patterns       -- Learned behavioral patterns
delegation_signals  -- Tasks needing delegation
weekly_review_items -- Parked tasks for review

-- Key fields added in Phase 3
tasks.rescheduled_for -- When to resurface task
tasks.parked_at      -- When task was parked
tasks.deleted_at     -- Soft delete timestamp
tasks.skip_action    -- What system did with skip
```

---

## Available Tools & Status

### Working Tools ✅
| Tool | Purpose | Status | Test Command |
|------|---------|--------|--------------|
| **CLI** | Pipeline testing | Working | `python cli.py --help` |
| **Web UI** | Task interface | Working | Open `localhost:8000` |
| **Processor** | LLM task extraction | Working | `python cli.py process` |
| **Skip Intelligence** | Smart skip handling | Working | Via UI skip button |
| **Pattern Learner** | Behavioral learning | Working | Auto-runs on skips |

### External Integrations
| Service | Purpose | Status | Configuration |
|---------|---------|--------|---------------|
| **Supabase** | Database | Connected | `.env` configured |
| **Anthropic** | Claude Opus LLM | Connected | API key in `.env` |
| **Redis** | Caching (Phase 4) | Available | `lyco-redis:6379` |
| **Gmail API** | Email capture | Ready | Credentials in place |
| **Calendar API** | Event capture | Ready | Credentials in place |

---

## How to Test Current Capabilities

### 1. Test Skip Intelligence
```bash
# Create a test task
python cli.py signal "Review Q4 budget projections"
python cli.py process

# Open web UI
open http://localhost:8000

# Click Skip and choose:
# - "wrong-time" → See rescheduling
# - "need-someone" → Check delegation_signals table
# - "not-now" → Will appear in weekly review
```

### 2. Test Pattern Learning  
```bash
# Skip similar tasks 3+ times
python test_phase3.py --test-patterns

# Check learned patterns
python -c "from src.pattern_learner import PatternLearner; pl = PatternLearner(); print(pl.get_patterns())"
```

### 3. Test Weekly Review
```bash
# Generate review email
python -c "from src.weekly_review import WeeklyReview; wr = WeeklyReview(); wr.generate_review()"
```

### 4. View Database State
```bash
# Connect to Supabase dashboard
# Or use SQL queries:
psql $DATABASE_URL -c "SELECT * FROM tasks WHERE completed_at IS NULL AND skipped_at IS NULL;"
psql $DATABASE_URL -c "SELECT * FROM skip_patterns ORDER BY frequency DESC;"
```

---

## File Structure

```
lyco-v2/
├── src/
│   ├── database.py           ✅ Core database operations
│   ├── processor.py          ✅ LLM task extraction  
│   ├── skip_intelligence.py  ✅ Smart skip handling
│   ├── pattern_learner.py    ✅ Behavioral pattern detection
│   ├── weekly_review.py      ✅ Weekly email generation
│   └── models.py             ✅ Data models
├── static/
│   └── index.html            ✅ Single-task UI
├── server.py                 ✅ FastAPI server
├── cli.py                    ✅ CLI testing interface
├── migrations/
│   └── phase3_skip_intelligence.sql ✅ Applied
└── .env                      ✅ Configured
```

---

## Performance Metrics

### Current Performance
- **Task Load Time**: ~2 seconds (needs optimization)
- **Skip Processing**: <500ms
- **Pattern Analysis**: Runs async, no user impact
- **Weekly Review Generation**: ~3 seconds

### Database Stats (as of last test)
- Total signals processed: 247
- Tasks created: 198
- Tasks completed: 112
- Tasks skipped: 73
- Patterns learned: 12
- Delegation signals: 8

---

## Known Limitations (To Address in Phase 4)

1. **No Caching**: Every request hits database
2. **No Background Processing**: Pattern analysis blocks on skip
3. **Basic Prompts**: No learning-based adjustments yet
4. **No Health Monitoring**: Manual intervention if issues
5. **No Weekly Insights**: Just review, not analytics

---

## Environment Variables

```bash
# Required (all configured)
SUPABASE_URL=https://[project].supabase.co
SUPABASE_KEY=[anon-key]
ANTHROPIC_API_KEY=sk-ant-[...]
DATABASE_URL=postgresql://[...]

# Optional (for Phase 4)
REDIS_URL=redis://localhost:6379
OPENAI_API_KEY=sk-[...] # Fallback LLM
```

---

## Startup Commands

```bash
# Start server
cd lyco-v2
source venv/bin/activate
python server.py

# In another terminal, test CLI
python cli.py next

# Open browser
open http://localhost:8000
```

---

## Troubleshooting

| Issue | Solution |
|-------|----------|
| Server won't start | Check port 8000 available: `lsof -i :8000` |
| Database connection failed | Verify `.env` has correct `SUPABASE_URL` |
| LLM not responding | Check `ANTHROPIC_API_KEY` is valid |
| Tasks not showing | Run `python cli.py process` to process signals |
| Skip not working | Check browser console for errors |

---

## Next Steps (Phase 4)

1. **Add Redis Caching** - Pre-fetch next 5 tasks
2. **Optimize Queries** - Composite indexes, materialized views
3. **Implement Learning** - Adjust prompts based on patterns
4. **Add Health Monitor** - Self-healing capabilities
5. **Polish UI** - Animations, keyboard shortcuts
6. **Generate Insights** - Weekly behavioral analysis

---

## Success Verification

Run these to confirm Phase 3 is working:
```bash
# Full system test
python test_phase3.py --full-test

# Should see:
# ✅ Skip intelligence working
# ✅ Patterns being learned
# ✅ Weekly review generated
# ✅ UI responsive
```

**System is ready for Phase 4 implementation!** 🚀