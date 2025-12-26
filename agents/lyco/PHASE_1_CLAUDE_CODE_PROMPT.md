# Claude Code Prompt: Build Lyco 2.0 Phase 1 - Foundation & Intelligence

## Mission
Build the core pipeline for Lyco 2.0, a cognitive prosthetic that captures task signals from reality and surfaces single next actions. This is Phase 1 (Weeks 1-2) focusing on the foundation and intelligence layer.

## Critical Context
- **User**: mene@beltlineconsulting.co (physician executive, CMO-level)
- **ADHD-optimized**: All tasks must be 15-minute chunks maximum
- **Energy windows**: High (9-11am), Medium (2-4pm), Low (after 4pm)
- **Core principle**: The system should never make the user think about the system itself
- **Architecture**: Signal capture → LLM processing → Single next action

## Directory Structure to Create
```
/Users/menedemestihas/Projects/demestihas-ai/agents/lyco-v2/
├── src/
│   ├── __init__.py
│   ├── database.py       # Supabase connection & queries
│   ├── processor.py      # LLM processing engine
│   ├── signals.py        # Signal capture logic
│   ├── tasks.py          # Task management
│   └── cli.py            # CLI interface
├── web/
│   └── index.html        # Single-page task interface
├── config/
│   ├── .env.example      # Environment variables template
│   └── schema.sql        # Database schema
├── tests/
│   ├── test_signals.json # 50+ example signals for testing
│   └── test_processor.py # Unit tests for LLM processing
├── docker/
│   ├── Dockerfile        # Python container setup
│   └── docker-compose.yml # Service orchestration
├── requirements.txt      # Python dependencies
└── README.md            # Setup and usage instructions
```

## Step 1: Database Schema
Create `config/schema.sql` with this exact schema:

```sql
-- Signals: Raw capture from reality
CREATE TABLE task_signals (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  source TEXT NOT NULL CHECK (source IN ('gmail', 'calendar', 'slack', 'pluma', 'huata', 'manual')),
  raw_content TEXT NOT NULL,
  processed BOOLEAN DEFAULT FALSE,
  processor_version TEXT DEFAULT '2.0.0',
  confidence_score FLOAT DEFAULT 0,
  timestamp TIMESTAMP DEFAULT NOW(),
  metadata JSONB DEFAULT '{}',
  user_id TEXT DEFAULT 'mene@beltlineconsulting.co'
);

-- Tasks: Processed, actionable items
CREATE TABLE tasks (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  signal_id UUID REFERENCES task_signals(id),
  content TEXT NOT NULL,
  next_action TEXT NOT NULL, -- Single concrete micro-step
  energy_level TEXT CHECK (energy_level IN ('high', 'medium', 'low', 'any')),
  time_estimate INTEGER DEFAULT 15,
  context_required JSONB DEFAULT '[]',
  deadline TIMESTAMP,
  completed_at TIMESTAMP,
  skipped_at TIMESTAMP,
  skipped_reason TEXT,
  metadata JSONB DEFAULT '{}'
);

-- Indexes for performance
CREATE INDEX idx_tasks_pending ON tasks(completed_at, skipped_at) 
  WHERE completed_at IS NULL AND skipped_at IS NULL;
CREATE INDEX idx_signals_unprocessed ON task_signals(processed) 
  WHERE processed = FALSE;

-- Row Level Security
ALTER TABLE task_signals ENABLE ROW LEVEL SECURITY;
ALTER TABLE tasks ENABLE ROW LEVEL SECURITY;

-- RLS Policies (for mene@beltlineconsulting.co)
CREATE POLICY "Users can view their own signals" ON task_signals
  FOR ALL USING (user_id = auth.email());

CREATE POLICY "Users can view their own tasks" ON tasks
  FOR ALL USING (signal_id IN (
    SELECT id FROM task_signals WHERE user_id = auth.email()
  ));
```

## Step 2: Core Python Implementation

### `src/database.py` - Supabase Connection
```python
import os
from supabase import create_client, Client
from typing import Dict, List, Optional
import json
from datetime import datetime

class Database:
    def __init__(self):
        url = os.environ.get("SUPABASE_URL")
        key = os.environ.get("SUPABASE_KEY")
        self.client: Client = create_client(url, key)
    
    async def create_signal(self, source: str, raw_content: str, metadata: Dict = None) -> str:
        """Create a new signal from any source"""
        data = {
            "source": source,
            "raw_content": raw_content,
            "metadata": metadata or {},
            "user_id": "mene@beltlineconsulting.co"
        }
        result = self.client.table('task_signals').insert(data).execute()
        return result.data[0]['id']
    
    async def get_unprocessed_signals(self, limit: int = 10) -> List[Dict]:
        """Get unprocessed signals for processing"""
        result = self.client.table('task_signals')\
            .select("*")\
            .eq('processed', False)\
            .limit(limit)\
            .execute()
        return result.data
    
    async def create_task(self, signal_id: str, task_data: Dict) -> str:
        """Create a task from processed signal"""
        data = {
            "signal_id": signal_id,
            "content": task_data['content'],
            "next_action": task_data['next_action'],
            "energy_level": task_data['energy_level'],
            "time_estimate": task_data.get('time_estimate', 15),
            "context_required": task_data.get('context_required', []),
            "metadata": task_data.get('metadata', {})
        }
        result = self.client.table('tasks').insert(data).execute()
        return result.data[0]['id']
    
    async def get_next_task(self, current_energy: str = None) -> Optional[Dict]:
        """Get the single next task based on current energy"""
        query = self.client.table('tasks')\
            .select("*")\
            .is_('completed_at', 'null')\
            .is_('skipped_at', 'null')
        
        if current_energy:
            query = query.eq('energy_level', current_energy)
        
        result = query.limit(1).execute()
        return result.data[0] if result.data else None
    
    async def complete_task(self, task_id: str) -> bool:
        """Mark task as complete"""
        self.client.table('tasks')\
            .update({'completed_at': datetime.now().isoformat()})\
            .eq('id', task_id)\
            .execute()
        return True
    
    async def skip_task(self, task_id: str, reason: str) -> bool:
        """Skip task with reason for learning"""
        self.client.table('tasks')\
            .update({
                'skipped_at': datetime.now().isoformat(),
                'skipped_reason': reason
            })\
            .eq('id', task_id)\
            .execute()
        return True
```

### `src/processor.py` - LLM Processing Engine
```python
import json
import os
from typing import Dict, Optional
from anthropic import Anthropic
import openai

class LLMProcessor:
    def __init__(self):
        self.anthropic = Anthropic(api_key=os.environ.get("ANTHROPIC_API_KEY"))
        openai.api_key = os.environ.get("OPENAI_API_KEY")
        self.model = "claude-3-opus-20240229"
    
    async def process_signal(self, signal: Dict) -> Optional[Dict]:
        """Process a signal with LLM to extract task if present"""
        
        prompt = f"""You are an executive assistant AI designed as a cognitive prosthetic.

Analyze this signal from {signal['source']}: {signal['raw_content']}

Context:
- User is mene@beltlineconsulting.co (physician executive, CMO-level)
- High energy: 9-11am (strategy, analysis, creation)
- Medium energy: 2-4pm (email, reviews, meetings)
- Low energy: after 4pm (reading, organizing)
- ADHD-optimized: tasks must be 15-minute chunks maximum
- Current time context will be provided separately

If this contains a commitment BY the user or request OF the user, return JSON:
{{
  "is_task": true,
  "content": "Human-readable task description",
  "next_action": "Single physical micro-step to begin (e.g., 'Open Gmail and type subject line')",
  "energy_level": "high|medium|low",
  "time_estimate": 15,
  "context_required": ["computer", "phone", "quiet"],
  "confidence": 0.0-1.0
}}

Examples of good next_action:
- "Open Gmail and type 'Q3 Report Status' in subject line"
- "Click Calendar tab and find 3pm slot"
- "Open Notion and create new page titled 'Meeting Notes'"
- "Text Cindy: 'Running 10 min late'"

If no actionable task found, return: {{"is_task": false}}
"""

        try:
            # Try Claude first
            response = self.anthropic.messages.create(
                model=self.model,
                max_tokens=500,
                messages=[{"role": "user", "content": prompt}]
            )
            result = json.loads(response.content[0].text)
            
        except Exception as e:
            print(f"Claude failed, falling back to GPT-4: {e}")
            # Fallback to GPT-4
            try:
                response = openai.ChatCompletion.create(
                    model="gpt-4-turbo-preview",
                    messages=[{"role": "user", "content": prompt}],
                    response_format={"type": "json_object"}
                )
                result = json.loads(response.choices[0].message.content)
            except Exception as e2:
                print(f"Both LLMs failed: {e2}")
                return None
        
        if result.get('is_task') and result.get('confidence', 0) > 0.5:
            return result
        return None
    
    def determine_current_energy(self) -> str:
        """Determine current energy level based on time"""
        from datetime import datetime
        hour = datetime.now().hour
        
        if 9 <= hour < 11:
            return "high"
        elif 14 <= hour < 16:
            return "medium"
        else:
            return "low"
```

### `src/cli.py` - CLI Testing Interface
```python
import click
import asyncio
from database import Database
from processor import LLMProcessor
from signals import SignalCapture
import json

db = Database()
processor = LLMProcessor()

@click.group()
def cli():
    """Lyco 2.0 Pipeline Testing"""
    pass

@cli.command()
@click.argument('text')
def signal(text):
    """Create a test signal"""
    async def create():
        signal_id = await db.create_signal('manual', text)
        click.echo(f"✓ Signal created: {signal_id}")
    asyncio.run(create())

@cli.command()
def process():
    """Process pending signals"""
    async def process_all():
        signals = await db.get_unprocessed_signals()
        processed = 0
        for sig in signals:
            result = await processor.process_signal(sig)
            if result and result.get('is_task'):
                await db.create_task(sig['id'], result)
                processed += 1
                click.echo(f"✓ Task created: {result['content'][:50]}...")
            # Mark signal as processed
            await db.client.table('task_signals')\
                .update({'processed': True})\
                .eq('id', sig['id'])\
                .execute()
        click.echo(f"Processed {len(signals)} signals, created {processed} tasks")
    asyncio.run(process_all())

@cli.command()
def next():
    """Get next task"""
    async def get_next():
        energy = processor.determine_current_energy()
        task = await db.get_next_task(energy)
        if task:
            click.echo(f"\n🎯 TASK: {task['content']}")
            click.echo(f"▶️  NEXT: {task['next_action']}")
            click.echo(f"⚡ Energy: {task['energy_level']} | ⏱️  {task['time_estimate']} min")
        else:
            click.echo("✨ Clear! Nothing pending.")
    asyncio.run(get_next())

@cli.command()
@click.argument('task_id')
def complete(task_id):
    """Mark task complete"""
    async def mark_complete():
        await db.complete_task(task_id)
        click.echo("🎉 Task completed!")
    asyncio.run(mark_complete())

@cli.command()
@click.argument('task_id')
@click.argument('reason')
def skip(task_id, reason):
    """Skip task with reason"""
    async def mark_skip():
        await db.skip_task(task_id, reason)
        click.echo(f"⏩ Task skipped: {reason}")
    asyncio.run(mark_skip())

@cli.command()
def test_pipeline():
    """Test the entire pipeline with sample data"""
    async def test():
        # Load test signals
        with open('tests/test_signals.json', 'r') as f:
            test_signals = json.load(f)
        
        click.echo("Testing signal capture...")
        for sig in test_signals[:5]:
            signal_id = await db.create_signal(sig['source'], sig['content'])
            click.echo(f"  ✓ {sig['source']}: {sig['content'][:30]}...")
        
        click.echo("\nProcessing signals...")
        await asyncio.sleep(1)
        signals = await db.get_unprocessed_signals()
        for sig in signals:
            result = await processor.process_signal(sig)
            if result and result.get('is_task'):
                click.echo(f"  ✓ Task detected: {result['content'][:40]}...")
        
        click.echo("\n✅ Pipeline test complete!")
    asyncio.run(test())

if __name__ == '__main__':
    cli()
```

## Step 3: Web Interface
Create `web/index.html` with the complete single-page interface:

```html
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Lyco 2.0</title>
    <style>
        * { margin: 0; padding: 0; box-sizing: border-box; }
        
        body {
            font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", system-ui, sans-serif;
            display: flex;
            justify-content: center;
            align-items: center;
            min-height: 100vh;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            padding: 20px;
        }
        
        #task-card {
            background: white;
            padding: 2rem;
            border-radius: 16px;
            box-shadow: 0 20px 25px -5px rgba(0,0,0,0.1), 0 10px 10px -5px rgba(0,0,0,0.04);
            max-width: 500px;
            width: 100%;
            transition: transform 0.2s;
        }
        
        #content {
            font-size: 1.5rem;
            font-weight: 600;
            color: #1f2937;
            margin-bottom: 1rem;
            line-height: 1.4;
        }
        
        #next-action {
            color: #6b7280;
            font-size: 1rem;
            margin: 1rem 0;
            padding: 1rem;
            background: #f9fafb;
            border-radius: 8px;
            border-left: 3px solid #8b5cf6;
        }
        
        #energy-indicator {
            display: flex;
            align-items: center;
            gap: 1rem;
            margin: 1rem 0;
            font-size: 0.875rem;
            color: #6b7280;
        }
        
        .energy-badge {
            padding: 0.25rem 0.75rem;
            border-radius: 9999px;
            font-weight: 500;
        }
        
        .energy-high { background: #fef3c7; color: #92400e; }
        .energy-medium { background: #dbeafe; color: #1e40af; }
        .energy-low { background: #f3e8ff; color: #5b21b6; }
        
        .actions {
            display: flex;
            gap: 1rem;
            margin-top: 1.5rem;
        }
        
        button {
            flex: 1;
            padding: 1rem;
            border: none;
            border-radius: 10px;
            cursor: pointer;
            font-weight: 600;
            font-size: 1rem;
            transition: all 0.2s;
            display: flex;
            align-items: center;
            justify-content: center;
            gap: 0.5rem;
        }
        
        button:active {
            transform: scale(0.95);
        }
        
        .complete {
            background: #10b981;
            color: white;
        }
        
        .complete:hover {
            background: #059669;
        }
        
        .skip {
            background: #f3f4f6;
            color: #6b7280;
        }
        
        .skip:hover {
            background: #e5e7eb;
        }
        
        #timer {
            margin-top: 1.5rem;
            text-align: center;
            font-size: 0.875rem;
            color: #9ca3af;
        }
        
        .celebration {
            animation: celebrate 0.6s ease-out;
        }
        
        @keyframes celebrate {
            0%, 100% { transform: scale(1) rotate(0deg); }
            25% { transform: scale(1.05) rotate(-2deg); }
            75% { transform: scale(1.05) rotate(2deg); }
        }
        
        .loading {
            text-align: center;
            color: #9ca3af;
        }
        
        .empty-state {
            text-align: center;
            padding: 2rem;
        }
        
        .empty-state h2 {
            color: #10b981;
            margin-bottom: 0.5rem;
        }
        
        .empty-state p {
            color: #6b7280;
            font-size: 0.875rem;
        }
    </style>
</head>
<body>
    <div id="task-card">
        <div class="loading">
            <h2>Loading...</h2>
        </div>
    </div>

    <script>
        let currentTask = null;
        let startTime = null;
        let timerInterval = null;
        
        // API base URL - update for production
        const API_BASE = window.location.hostname === 'localhost' 
            ? 'http://localhost:8000/api' 
            : '/api';

        async function loadNextTask() {
            try {
                const response = await fetch(`${API_BASE}/next-task`);
                const data = await response.json();
                
                if (data.task) {
                    displayTask(data.task);
                } else {
                    displayEmptyState();
                }
            } catch (error) {
                console.error('Failed to load task:', error);
                displayError();
            }
        }

        function displayTask(task) {
            currentTask = task;
            startTime = Date.now();
            
            const card = document.getElementById('task-card');
            card.innerHTML = `
                <h2 id="content">${task.content}</h2>
                <div id="next-action">
                    <strong>First step:</strong> ${task.next_action}
                </div>
                <div id="energy-indicator">
                    <span class="energy-badge energy-${task.energy_level}">
                        ${task.energy_level} energy
                    </span>
                    <span>⏱️ ${task.time_estimate} min</span>
                </div>
                <div class="actions">
                    <button class="complete" onclick="completeTask()">
                        ✓ Done
                    </button>
                    <button class="skip" onclick="skipTask()">
                        Skip →
                    </button>
                </div>
                <div id="timer">0:00</div>
            `;
            
            startTimer();
        }

        function displayEmptyState() {
            currentTask = null;
            stopTimer();
            
            const card = document.getElementById('task-card');
            card.innerHTML = `
                <div class="empty-state">
                    <h2>✨ All Clear!</h2>
                    <p>Nothing pending. Checking for new tasks in 30 seconds...</p>
                </div>
            `;
            
            // Auto-refresh after 30 seconds
            setTimeout(loadNextTask, 30000);
        }

        function displayError() {
            const card = document.getElementById('task-card');
            card.innerHTML = `
                <div class="empty-state">
                    <h2>Connection Error</h2>
                    <p>Retrying in 5 seconds...</p>
                </div>
            `;
            setTimeout(loadNextTask, 5000);
        }

        async function completeTask() {
            if (!currentTask) return;
            
            // Immediate visual feedback
            const card = document.getElementById('task-card');
            card.classList.add('celebration');
            
            try {
                await fetch(`${API_BASE}/tasks/${currentTask.id}/complete`, {
                    method: 'POST'
                });
                
                // Show celebration then load next
                setTimeout(() => {
                    card.classList.remove('celebration');
                    loadNextTask();
                }, 600);
            } catch (error) {
                console.error('Failed to complete task:', error);
                card.classList.remove('celebration');
            }
        }

        async function skipTask() {
            if (!currentTask) return;
            
            const reasons = [
                'low-energy',
                'no-time',
                'missing-context',
                'not-important',
                'blocked',
                'other'
            ];
            
            const reason = prompt(
                'Quick - why skip?\n\n' + 
                reasons.map((r, i) => `${i+1}. ${r}`).join('\n') +
                '\n\nEnter number or custom reason:'
            );
            
            if (reason) {
                const finalReason = reasons[parseInt(reason) - 1] || reason;
                
                try {
                    await fetch(`${API_BASE}/tasks/${currentTask.id}/skip`, {
                        method: 'POST',
                        headers: {'Content-Type': 'application/json'},
                        body: JSON.stringify({reason: finalReason})
                    });
                    loadNextTask();
                } catch (error) {
                    console.error('Failed to skip task:', error);
                }
            }
        }

        function startTimer() {
            stopTimer();
            timerInterval = setInterval(updateTimer, 1000);
        }

        function stopTimer() {
            if (timerInterval) {
                clearInterval(timerInterval);
                timerInterval = null;
            }
        }

        function updateTimer() {
            if (!startTime) return;
            
            const elapsed = Math.floor((Date.now() - startTime) / 1000);
            const minutes = Math.floor(elapsed / 60);
            const seconds = elapsed % 60;
            
            document.getElementById('timer').textContent = 
                `${minutes}:${seconds.toString().padStart(2, '0')}`;
        }

        // Initial load
        loadNextTask();
        
        // Keyboard shortcuts
        document.addEventListener('keydown', (e) => {
            if (!currentTask) return;
            
            if (e.key === 'Enter' || e.key === 'd') {
                completeTask();
            } else if (e.key === 's' || e.key === 'ArrowRight') {
                skipTask();
            }
        });

        // Auto-refresh if idle for too long
        setInterval(() => {
            if (currentTask && Date.now() - startTime > 300000) { // 5 minutes
                loadNextTask();
            }
        }, 60000);
    </script>
</body>
</html>
```

## Step 4: Test Data
Create `tests/test_signals.json` with diverse examples:

```json
[
  {
    "source": "gmail",
    "content": "I'll send you the Q3 report by Friday"
  },
  {
    "source": "gmail", 
    "content": "Can you review the budget proposal and get back to me?"
  },
  {
    "source": "calendar",
    "content": "Prepare slides for tomorrow's board meeting at 2pm"
  },
  {
    "source": "slack",
    "content": "@mene can you approve the new hire requisition?"
  },
  {
    "source": "gmail",
    "content": "Thanks for lunch! The weather was nice today."
  },
  {
    "source": "manual",
    "content": "Call Jim about the contract renewal"
  },
  {
    "source": "pluma",
    "content": "Follow up with Sarah about clinical trial results"
  },
  {
    "source": "huata",
    "content": "Team standup in 30 minutes - need status updates"
  }
]
```

## Step 5: Docker Configuration

### `docker/Dockerfile`:
```dockerfile
FROM python:3.11-slim

WORKDIR /app

RUN apt-get update && apt-get install -y \
    gcc \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY src/ ./src/
COPY web/ ./web/
COPY tests/ ./tests/

ENV PYTHONPATH=/app

CMD ["python", "-m", "src.cli", "test-pipeline"]
```

### `requirements.txt`:
```
supabase==2.0.0
anthropic==0.18.0
openai==1.12.0
click==8.1.7
redis==5.0.1
python-dotenv==1.0.0
fastapi==0.109.0
uvicorn==0.27.0
asyncio==3.4.3
pytest==8.0.0
pytest-asyncio==0.23.0
```

## Step 6: Environment Configuration

### `.env.example`:
```bash
# Supabase
SUPABASE_URL=https://your-project.supabase.co
SUPABASE_KEY=your-anon-key

# LLM APIs
ANTHROPIC_API_KEY=sk-ant-...
OPENAI_API_KEY=sk-...

# Redis (existing)
REDIS_URL=redis://lyco-redis:6379

# User config
USER_EMAIL=mene@beltlineconsulting.co
HIGH_ENERGY_HOURS=9-11
MEDIUM_ENERGY_HOURS=14-16
LOW_ENERGY_HOURS=16-22
```

## Implementation Order

1. **First**: Set up directory structure and copy all files
2. **Second**: Configure Supabase database with schema
3. **Third**: Set up environment variables
4. **Fourth**: Test database connection with CLI
5. **Fifth**: Test LLM processing with sample signals
6. **Sixth**: Open web interface and test full flow

## Testing Commands

```bash
# Test database connection
python -m src.cli signal "Test task from CLI"

# Process signals
python -m src.cli process

# Get next task
python -m src.cli next

# Run full pipeline test
python -m src.cli test-pipeline

# Start web server (in separate terminal)
cd web && python -m http.server 8080
```

## Success Criteria

✅ CLI can create, process, and retrieve tasks
✅ HTML interface shows current task within 2 seconds
✅ LLM correctly identifies 90% of test commitments
✅ Tasks have concrete next actions (not abstract)
✅ Energy levels match time of day
✅ Skip reasons are captured for learning

## Key Implementation Notes

1. **No complex UI** - Single task view only
2. **No manual entry** - Everything from signals
3. **LLM-first** - No regex or brittle parsing
4. **Instant feedback** - Celebrations and transitions
5. **ADHD-optimized** - 15-minute chunks, clear next actions
6. **Learning system** - Track skip reasons for improvement

## Next Phase Preview

After Phase 1 is complete and tested, Phase 2 will add:
- Redis integration with existing Pluma/Huata agents
- Background Docker container for continuous processing
- 5-minute polling cycle
- Energy pattern learning

Build this foundation first, test thoroughly, then we'll add intelligence layers.
