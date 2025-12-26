# Lyco 2.0: Cognitive Prosthetic for Ambient Task Intelligence

Lyco 2.0 is not a task manager. It's a cognitive prosthetic that externalizes executive function, capturing signals from reality and surfacing single actions at optimal energy moments.

## Core Principle

> "Any feature that forces the user to think about the system rather than about the task represents a failure."

## Quick Start

### Prerequisites

- Python 3.11+
- Docker & Docker Compose (optional)
- Supabase account
- Anthropic API key (Claude)
- OpenAI API key (optional fallback)

### Installation

1. **Clone and setup:**
```bash
cd /Users/menedemestihas/Projects/demestihas-ai/agents/lyco/lyco-v2
chmod +x setup.sh
./setup.sh
```

2. **Configure environment:**
```bash
cp .env.example .env
# Edit .env with your API keys
```

3. **Setup database:**
   - Go to your Supabase dashboard
   - Open SQL editor
   - Run the contents of `schema.sql`

4. **Test the system:**
```bash
# Activate virtual environment
source venv/bin/activate

# Run test signals
python cli.py test

# Start the server
python server.py

# Open browser to http://localhost:8000
```

## Architecture

### Two-Track Development

1. **Backend Pipeline (CLI)** - Test data processing
2. **Experience Validation (UI)** - Minimal interface for task display

### Components

- **Intelligence Engine**: LLM-powered task extraction
- **Database Manager**: Supabase integration
- **Background Processor**: Continuous signal processing
- **Web Server**: FastAPI server for UI and API
- **CLI**: Command-line testing interface

## Usage

### CLI Commands

```bash
# Create a signal
python cli.py signal "I'll send the report by Friday"

# Process all pending signals
python cli.py process

# Get next task
python cli.py next

# Complete a task
python cli.py complete <task_id>

# Skip a task
python cli.py skip <task_id> --reason "low-energy"

# Check status
python cli.py status

# Run test signals
python cli.py test
```

### API Endpoints

- `GET /` - Main UI
- `GET /api/next-task` - Get next task
- `POST /api/tasks/{id}/complete` - Mark task complete
- `POST /api/tasks/{id}/skip` - Skip task with reason
- `GET /api/status` - System status
- `POST /api/process` - Trigger processing

## Docker Deployment

```bash
# Deploy with Docker
chmod +x deploy.sh
./deploy.sh

# View logs
docker-compose logs -f

# Stop containers
docker-compose down
```

## Integration with Other Agents

Lyco 2.0 integrates with existing agents via Redis:

- **Pluma**: Email intelligence
- **Huata**: Calendar management
- **Yanay**: Orchestration

Signals are captured from these agents automatically every 5 minutes.

## Energy Levels

Tasks are categorized by energy requirements:

- **High** (9-11am): Strategy, analysis, creation
- **Medium** (2-4pm): Email, reviews, meetings  
- **Low** (after 4pm): Reading, organizing

## Key Features

✓ **Single task visibility** - No overwhelming lists
✓ **Ambient capture** - Automatic signal collection
✓ **LLM intelligence** - Semantic understanding
✓ **Skip learning** - Track and learn from skipped tasks
✓ **ADHD optimized** - 15-minute micro-tasks
✓ **Instant rewards** - Dopamine-engineered celebrations

## What This Is NOT

❌ No task lists or queues
❌ No complex categorization
❌ No planning interfaces
❌ No manual task entry
❌ No productivity dashboards

## Configuration

Edit `.env` file:

```env
SUPABASE_URL=your_supabase_url
SUPABASE_ANON_KEY=your_supabase_anon_key
ANTHROPIC_API_KEY=your_anthropic_api_key
OPENAI_API_KEY=your_openai_api_key  # Optional
REDIS_URL=redis://localhost:6379
```

## Development

### Project Structure

```
lyco-v2/
├── src/
│   ├── models.py       # Data models
│   ├── database.py     # Supabase integration
│   └── processor.py    # LLM intelligence engine
├── static/
│   └── index.html      # Minimal UI
├── cli.py              # CLI interface
├── server.py           # FastAPI server
├── processor.py        # Background processor
├── requirements.txt    # Python dependencies
├── Dockerfile          # Container definition
├── docker-compose.yml  # Multi-container setup
├── schema.sql          # Database schema
├── setup.sh            # Setup script
├── deploy.sh           # Deployment script
└── README.md           # This file
```

### Testing

```bash
# Run unit tests (when implemented)
pytest tests/

# Test with CLI
python cli.py test

# Manual testing
python cli.py signal "Test commitment"
python cli.py process
python cli.py next
```

## Monitoring

- **Supabase Dashboard**: Monitor database
- **Redis Monitor**: `redis-cli monitor`
- **Docker Logs**: `docker-compose logs -f`
- **Browser DevTools**: Network tab for API calls

## Troubleshooting

### Common Issues

1. **No tasks appearing**
   - Check API keys in `.env`
   - Verify Supabase schema is created
   - Check processor logs

2. **LLM errors**
   - Verify ANTHROPIC_API_KEY
   - Check API rate limits
   - Fallback to GPT-4 if configured

3. **Database connection**
   - Verify SUPABASE_URL and SUPABASE_ANON_KEY
   - Check Supabase service status

## Success Metrics

- **Time to Action**: < 5 seconds
- **Capture Coverage**: 90%+ of commitments
- **Task Completion Rate**: 60%+
- **Energy Match Rate**: 70%+

## Roadmap

### Phase 1: Foundation (Weeks 1-2) ✅
- Core pipeline
- LLM processor
- Basic UI

### Phase 2: Ambient Capture (Weeks 3-4)
- Agent integration
- Automated collection
- Energy classification

### Phase 3: Flow Optimization (Weeks 5-6)
- ADHD optimizations
- Micro-actions
- Skip analysis

### Phase 4: Intelligence (Week 7)
- Pattern learning
- Performance optimization
- Weekly insights

## License

Proprietary - Beltline Consulting

## Support

For issues or questions, contact: mene@beltlineconsulting.co