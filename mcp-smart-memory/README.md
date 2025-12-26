# Smart MCP Memory Server

A Model Context Protocol (MCP) server that provides intelligent memory management for Claude Desktop with active learning capabilities.

## Features

- 🧠 **Active Learning** - Automatically identifies valuable information during conversations
- 👤 **Human-in-the-Loop** - Always asks for confirmation before storing memories
- 🔍 **Pattern Detection** - Recognizes and stores workflow patterns
- 🌐 **HTTP API** - RESTful API for browser extensions and external tools
- 📚 **Context Retrieval** - Finds relevant memories for current topics
- ⚠️ **Conflict Detection** - Checks for contradictory information
- 📝 **Session Summaries** - Creates summaries of conversation sessions

## Installation

```bash
cd ~/Projects/demestihas-ai/mcp-smart-memory
npm install
```

## Running

```bash
# Start MCP server (for Claude Desktop)
npm start

# Start HTTP API (for browser extensions) 
npm run api

# Development mode with auto-reload
npm run dev
```

## Claude Desktop Configuration

Add to `~/Library/Application Support/Claude/claude_desktop_config.json`:

```json
{
  "mcpServers": {
    "smart-memory": {
      "command": "node",
      "args": ["/Users/menedemestihas/Projects/demestihas-ai/mcp-smart-memory/index.js"]
    }
  }
}
```

After adding the configuration, restart Claude Desktop to load the MCP server.

## Available Tools in Claude Desktop

### 1. `analyze_for_memory`
Analyzes conversation to find valuable information worth remembering.
- Scans for solutions, configurations, decisions, errors, and insights
- Returns categorized findings with importance levels

### 2. `propose_memory`
Proposes specific information to store in memory.
- Requires: content, category, importance, and rationale
- Creates a pending memory with unique ID for confirmation

### 3. `confirm_and_store`
Stores memory after user confirmation.
- Requires memory ID and user confirmation
- Supports user edits before storing

### 4. `detect_patterns_in_conversation`
Identifies workflow patterns in the conversation.
- Analyzes sequences of actions and tools used
- Proposes pattern storage for reusable workflows

### 5. `get_relevant_context`
Retrieves relevant memories for the current topic.
- Searches memory database for related information
- Returns ranked results with relevance scores

### 6. `track_decision`
Records important decisions with reasoning.
- Captures decision, reasoning, alternatives, and expected impact
- Useful for documenting architectural choices

### 7. `remember_error_and_fix`
Stores errors and their solutions for future reference.
- Records error messages, solutions, context, and prevention tips
- Helps avoid repeating the same mistakes

### 8. `session_summary`
Creates a summary of the current session.
- Documents topics covered, problems solved, and key insights
- Tracks next steps and TODOs

### 9. `check_memory_conflicts`
Checks for conflicting information in memory.
- Identifies contradictory information before storing
- Helps maintain consistency in the knowledge base

## Usage in Claude Desktop

1. Start a conversation normally
2. Claude will periodically analyze the conversation for valuable information
3. When valuable information is found, Claude will propose storing it
4. Review the proposal and confirm or edit before storing
5. Information becomes available in all future conversations

### Example Workflow

```
User: "I fixed the Docker issue by adding --network host to the run command"

Claude: Let me analyze this for valuable information...
[Uses analyze_for_memory tool]

Claude: I found a solution worth remembering. Let me propose it:
[Uses propose_memory tool]

📝 MEMORY PROPOSAL (ID: abc-123)
Category: solution
Importance: high
Content: Fixed Docker networking issue by adding --network host flag to docker run command
Rationale: Important troubleshooting solution for Docker networking

Would you like me to store this memory? (I'll use confirm_and_store)

User: Yes, please store it

Claude: [Uses confirm_and_store tool]
✅ Memory stored successfully!
```

## HTTP API Usage

The HTTP API runs on port 7777 and provides RESTful endpoints:

### Get Context
```bash
curl "http://localhost:7777/context?q=docker+networking&limit=5"
```

### Store Memory
```bash
curl -X POST http://localhost:7777/store \
  -H "Content-Type: application/json" \
  -d '{
    "content": "Docker networking fix: use --network host",
    "type": "solution",
    "importance": "high"
  }'
```

### Augment Prompt
```bash
curl -X POST http://localhost:7777/augment \
  -H "Content-Type: application/json" \
  -d '{
    "prompt": "How do I fix Docker networking?",
    "max_context": 3
  }'
```

### Analyze Text
```bash
curl -X POST http://localhost:7777/analyze \
  -H "Content-Type: application/json" \
  -d '{
    "text": "I discovered that adding --network host fixed the issue",
    "focus_areas": ["solution", "discovery"]
  }'
```

### Health Check
```bash
curl http://localhost:7777/health
```

## API Endpoints

- `GET /health` - System health and statistics
- `GET /context?q=query&limit=5` - Get relevant context for a query
- `POST /augment` - Augment a prompt with relevant context
- `POST /store` - Store a new memory
- `GET /patterns?q=query` - Find matching patterns
- `POST /analyze` - Analyze text for memorable content

## Memory Categories

- **solution** - Problem solutions and fixes
- **configuration** - Settings, paths, environment variables
- **error_fix** - Error messages and their resolutions
- **decision** - Important decisions with reasoning
- **workflow** - Repeatable process patterns
- **insight** - Key learnings and discoveries
- **command** - Useful commands and scripts
- **note** - General notes and information

## Integration with Existing RAG System

This server integrates with your existing RAG system at `../claude-desktop-rag/`:
- Uses the initialized memory store for persistence
- Leverages context retriever for similarity search
- Employs pattern detector for workflow identification

## Browser Extension Integration

The HTTP API can be used by browser extensions to:
1. Store important information from web pages
2. Augment search queries with context
3. Analyze selected text for memorable content
4. Retrieve relevant memories while browsing

## Development

For development with auto-reload:
```bash
npm run dev
```

Monitor logs:
- MCP server logs to stderr (visible in Claude Desktop logs)
- API server logs to stdout

## Troubleshooting

1. **MCP server not appearing in Claude Desktop**
   - Check configuration file path is correct
   - Restart Claude Desktop after configuration changes
   - Check Claude Desktop logs for errors

2. **Memory system not initializing**
   - Ensure `claude-desktop-rag` project is in the parent directory
   - Check that the RAG system dependencies are installed
   - Server will fall back to mock implementation if RAG system unavailable

3. **API server connection refused**
   - Check port 7777 is not in use
   - Ensure firewall allows local connections
   - Try alternative port with `PORT=8888 npm run api`

## License

MIT

## Author

Demestihas.ai