# SUPABASE SETUP - 3:30 PM Sprint
**Time:** September 2, 2025 - 3:30 PM
**Duration:** 30 minutes
**Energy Level:** MEDIUM (post-orientation, caffeinated)

## ⏱️ TIME BREAKDOWN

### Minutes 0-5: Account Setup
1. Go to https://supabase.com
2. Sign in with GitHub (fastest)
3. Create new project: "demestihas-memory"
4. **IMPORTANT:** Copy these immediately:
   - Project URL: _____________
   - Anon Public Key: _____________
   - Service Role Key: _____________

### Minutes 5-15: Database Creation

Copy and paste this ENTIRE block into SQL Editor:

```sql
-- RUN THIS ENTIRE BLOCK AT ONCE

-- Enable UUID extension
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- Conversations tracking
CREATE TABLE conversations (
    id UUID DEFAULT uuid_generate_v4() PRIMARY KEY,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW(),
    title TEXT,
    summary TEXT,
    participants TEXT[],
    tags TEXT[],
    thread_id TEXT,
    importance TEXT DEFAULT 'medium'
);

-- Tasks with ADHD metadata
CREATE TABLE tasks (
    id UUID DEFAULT uuid_generate_v4() PRIMARY KEY,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW(),
    completed_at TIMESTAMPTZ,
    title TEXT NOT NULL,
    description TEXT,
    priority TEXT DEFAULT 'medium',
    energy_required TEXT DEFAULT 'medium',
    estimated_minutes INTEGER DEFAULT 30,
    assigned_to TEXT DEFAULT 'Mene',
    tags TEXT[],
    source TEXT,
    parent_conversation UUID REFERENCES conversations(id)
);

-- Family patterns learning
CREATE TABLE family_patterns (
    id UUID DEFAULT uuid_generate_v4() PRIMARY KEY,
    observed_at TIMESTAMPTZ DEFAULT NOW(),
    pattern_type TEXT,
    description TEXT,
    frequency INTEGER DEFAULT 1,
    impact TEXT DEFAULT 'medium',
    family_member TEXT,
    confidence FLOAT DEFAULT 0.5
);

-- Quick captures from voice/text
CREATE TABLE quick_captures (
    id UUID DEFAULT uuid_generate_v4() PRIMARY KEY,
    captured_at TIMESTAMPTZ DEFAULT NOW(),
    processed_at TIMESTAMPTZ,
    content TEXT,
    source TEXT, -- 'voice', 'text', 'email', 'calendar'
    intent TEXT, -- 'task', 'reminder', 'note', 'question'
    processed BOOLEAN DEFAULT FALSE
);

-- Daily summaries
CREATE TABLE daily_summaries (
    id UUID DEFAULT uuid_generate_v4() PRIMARY KEY,
    date DATE DEFAULT CURRENT_DATE,
    energy_level TEXT,
    completed_count INTEGER DEFAULT 0,
    captured_count INTEGER DEFAULT 0,
    key_decisions TEXT[],
    tomorrow_priorities TEXT[],
    patterns_observed TEXT[]
);

-- Create indexes for fast retrieval
CREATE INDEX idx_tasks_assigned ON tasks(assigned_to);
CREATE INDEX idx_tasks_priority ON tasks(priority);
CREATE INDEX idx_conversations_updated ON conversations(updated_at DESC);
CREATE INDEX idx_captures_processed ON quick_captures(processed);
CREATE INDEX idx_patterns_member ON family_patterns(family_member);

-- Create a view for today's tasks
CREATE VIEW todays_tasks AS
SELECT * FROM tasks 
WHERE DATE(created_at) = CURRENT_DATE 
   OR (completed_at IS NULL AND priority = 'urgent')
ORDER BY priority DESC, energy_required ASC;

-- Success check
SELECT 'SUCCESS: All tables created!' as status;
```

### Minutes 15-20: Python Connection Test

Create file: `~/Projects/demestihas-ai/claude-desktop/test_supabase.py`

```python
from supabase import create_client
import os
from datetime import datetime

# Your credentials (fill these in)
SUPABASE_URL = "YOUR_URL_HERE"
SUPABASE_KEY = "YOUR_ANON_KEY_HERE"

# Initialize client
supabase = create_client(SUPABASE_URL, SUPABASE_KEY)

# Test 1: Create a task
print("Test 1: Creating task...")
task = supabase.table('tasks').insert({
    "title": "Consilium application review",
    "priority": "urgent",
    "energy_required": "high",
    "estimated_minutes": 30,
    "assigned_to": "Mene"
}).execute()
print(f"✅ Task created: {task.data[0]['id']}")

# Test 2: Create a quick capture
print("\nTest 2: Creating quick capture...")
capture = supabase.table('quick_captures').insert({
    "content": "Remember to ask Cindy about Spirit Day logistics",
    "source": "voice",
    "intent": "reminder"
}).execute()
print(f"✅ Capture created: {capture.data[0]['id']}")

# Test 3: Log a family pattern
print("\nTest 3: Logging family pattern...")
pattern = supabase.table('family_patterns').insert({
    "pattern_type": "priority_inflation",
    "description": "User marks everything as urgent",
    "family_member": "Mene",
    "impact": "high",
    "confidence": 0.9
}).execute()
print(f"✅ Pattern logged: {pattern.data[0]['id']}")

# Test 4: Retrieve today's tasks
print("\nTest 4: Getting today's tasks...")
tasks = supabase.table('todays_tasks').select("*").execute()
print(f"✅ Found {len(tasks.data)} tasks for today")
for task in tasks.data:
    print(f"  - {task['title']} ({task['priority']})")

print("\n🎉 ALL TESTS PASSED! Supabase is connected!")
```

### Minutes 20-25: Run the Test

```bash
# Install Supabase client
pip install supabase

# Run the test
python ~/Projects/demestihas-ai/claude-desktop/test_supabase.py
```

### Minutes 25-30: Create Integration File

Save as: `~/Projects/demestihas-ai/claude-desktop/memory_integration.py`

```python
import os
from supabase import create_client
from datetime import datetime, timedelta
import json

class DemestihasMemory:
    def __init__(self):
        self.url = "YOUR_SUPABASE_URL"
        self.key = "YOUR_SUPABASE_KEY"
        self.client = create_client(self.url, self.key)
    
    # Quick methods for common operations
    def quick_task(self, title, priority="medium"):
        """Add a task in one line"""
        return self.client.table('tasks').insert({
            "title": title,
            "priority": priority,
            "created_at": datetime.now().isoformat()
        }).execute()
    
    def capture(self, content, source="text"):
        """Capture anything quickly"""
        return self.client.table('quick_captures').insert({
            "content": content,
            "source": source,
            "captured_at": datetime.now().isoformat()
        }).execute()
    
    def whats_urgent(self):
        """Get all urgent items"""
        return self.client.table('tasks')\
            .select("*")\
            .eq('priority', 'urgent')\
            .is_('completed_at', 'null')\
            .execute()
    
    def todays_summary(self):
        """Generate summary for today"""
        today = datetime.now().date()
        
        # Get completed tasks
        completed = self.client.table('tasks')\
            .select("*")\
            .gte('completed_at', today.isoformat())\
            .execute()
        
        # Get captures
        captures = self.client.table('quick_captures')\
            .select("*")\
            .gte('captured_at', today.isoformat())\
            .execute()
        
        return {
            "date": today.isoformat(),
            "completed": len(completed.data),
            "captured": len(captures.data),
            "items": completed.data
        }

# Usage:
# memory = DemestihasMemory()
# memory.quick_task("Review Consilium application", "urgent")
# memory.capture("Kids need spirit wear Thursday")
# urgent = memory.whats_urgent()
```

## 🎯 SUCCESS CRITERIA

By 4:00 PM, you should have:
- [ ] Supabase project created
- [ ] All tables successfully created
- [ ] Test script runs without errors
- [ ] At least 3 items in the database
- [ ] Integration file ready for tomorrow

## 🚫 COMMON PITFALLS TO AVOID

1. **DON'T** try to make it perfect - just get it working
2. **DON'T** forget to save your credentials immediately
3. **DON'T** skip the test script - it validates everything
4. **DON'T** worry about the vector embeddings yet - that's v2

## 🆘 IF SOMETHING FAILS

**SQL errors?**
- The tables might already exist
- Run: `DROP TABLE IF EXISTS [tablename] CASCADE;` then retry

**Python connection errors?**
- Check URL format: should start with `https://`
- Check key: should be long string starting with `eyJ`

**Import errors?**
- Make sure you ran: `pip install supabase`

## 📱 Quick Mobile Access

Once set up, you can access from anywhere:
- Supabase has a mobile app
- Your tables are accessible via REST API
- Can create iOS Shortcuts for quick capture

---

**At 3:30 PM, just open this file and execute step by step. Don't think, just copy-paste. The system will guide you.**