# Claude Desktop RAG System
## Chapter 1: The Memory Palace - Demestihas.ai MAS

A sophisticated Retrieval-Augmented Generation (RAG) system for Claude Desktop that provides intelligent context injection, pattern detection, and dual-storage memory management.

## Features

- **Hybrid Storage**: Local SQLite cache + Supabase cloud persistence
- **OpenAI Embeddings**: Uses text-embedding-3-small (1536 dimensions)
- **Pattern Detection**: Automatically detects and learns workflow patterns
- **Context Injection**: Intelligent prompt augmentation with relevant context
- **Dynamic Ranking**: Multi-factor relevance scoring with recency and importance weights
- **Real-time Sync**: Asynchronous cloud synchronization with local-first architecture

## Architecture

```
claude-desktop-rag/
├── src/
│   ├── core/               # Core services
│   │   ├── embedding-service.js    # OpenAI embeddings with caching
│   │   ├── supabase-client.js      # Cloud storage client
│   │   └── sqlite-client.js        # Local cache client
│   ├── memory/             # Memory management
│   │   ├── memory-store.js         # Dual storage orchestration
│   │   ├── context-retriever.js    # RAG retrieval engine
│   │   └── memory-ranker.js        # Result ranking algorithms
│   ├── patterns/           # Pattern detection
│   │   ├── pattern-detector.js     # Workflow pattern detection
│   │   ├── pattern-matcher.js      # Pattern application engine
│   │   └── pattern-store.js        # Pattern persistence
│   └── claude-desktop/     # Claude Desktop integration
│       ├── extension-hooks.js      # Event hooks for Claude
│       ├── context-injector.js     # Prompt augmentation
│       └── response-handler.js     # Response processing
```

## Quick Start

### Prerequisites

- Node.js 18+
- OpenAI API key
- Supabase account (optional for cloud storage)

### Installation

1. Clone the repository:
```bash
git clone <repository-url>
cd claude-desktop-rag
```

2. Run the setup script:
```bash
chmod +x scripts/setup.sh
./scripts/setup.sh
```

3. Configure your environment:
```bash
cp .env.template .env
# Edit .env with your API keys
```

4. Set up Supabase (optional):
```sql
-- Run the schema in your Supabase SQL editor
-- File: config/supabase-schema.sql
```

5. Start the system:
```bash
npm start
# or
./start.sh
```

## Configuration

Edit `.env` file with your credentials:

```env
# OpenAI
OPENAI_API_KEY=sk-...

# Supabase (optional)
SUPABASE_URL=https://xxxxx.supabase.co
SUPABASE_ANON_KEY=eyJ...
SUPABASE_SERVICE_ROLE_KEY=eyJ...

# RAG Settings
SIMILARITY_THRESHOLD=0.70
PATTERN_THRESHOLD=0.80
MAX_CONTEXT_ITEMS=15
```

## Usage

### Basic Integration

```javascript
import ragSystem from './src/index.js';

// Initialize
await ragSystem.initialize();

// Process a prompt with context
const augmented = await ragSystem.processPrompt(
  "How do I implement authentication?",
  { contextType: 'code' }
);

// Handle Claude's response
const processed = await ragSystem.handleResponse(
  claudeResponse,
  { prompt: originalPrompt }
);
```

### Store Memories

```javascript
// Store an interaction
await ragSystem.storeMemory("User implemented OAuth2 authentication", {
  interactionType: 'implementation',
  filePaths: ['src/auth/oauth.js'],
  toolChain: ['create-file', 'edit-file'],
  successScore: 1.0
});
```

### Retrieve Context

```javascript
// Get relevant context for a query
const context = await ragSystem.retrieveContext(
  "authentication setup",
  { maxItems: 10 }
);

console.log(`Found ${context.items.length} relevant memories`);
console.log(`Detected ${context.patterns?.length || 0} patterns`);
```

## Claude Desktop Integration

### Extension Hooks

The system provides hooks for Claude Desktop events:

```javascript
import extensionHooks from './src/claude-desktop/extension-hooks.js';

// Register custom hook
extensionHooks.registerHook('pre-prompt', async (data) => {
  // Augment prompt before sending to Claude
  return augmentedData;
});

// Handle events
await extensionHooks.handleEvent('pre-prompt', {
  prompt: userPrompt,
  metadata: {}
});
```

### Context Injection Templates

Multiple templates are available for different contexts:

- `default`: General purpose context
- `code`: Code-focused context with syntax highlighting
- `documentation`: Documentation with sections and links
- `conversation`: Conversational context with history

```javascript
import contextInjector from './src/claude-desktop/context-injector.js';

const result = await contextInjector.injectContext(
  prompt,
  { templateName: 'code' }
);
```

## Pattern Detection

The system automatically detects repeated workflows:

- **Threshold**: 0.80 similarity score
- **Min Occurrences**: 3 times within 7 days
- **Auto-apply**: Enabled after 5 successful uses with >90% success rate

Patterns are stored with:
- Trigger embedding for matching
- Action sequence (tools, files, templates)
- Success rate tracking
- Project context association

## Testing

Run the comprehensive test suite:

```bash
npm test
# or
node scripts/test-pipeline.js
```

Tests cover:
- Embedding generation and similarity
- Database connections (SQLite & Supabase)
- Memory storage and retrieval
- Context retrieval with ranking
- Pattern detection and matching
- Claude Desktop integration hooks

## Performance

- **Embedding Cache**: 1-hour TTL with LRU eviction
- **Local Cache**: Max 1000 items, 24-hour retention
- **Retrieval**: <1 second for 15 context items
- **Batch Processing**: Up to 100 embeddings per request
- **Parallel Search**: Local and cloud queries run concurrently

## Monitoring

Check system statistics:

```javascript
const stats = await ragSystem.getStats();
console.log(stats);
// {
//   memory: { local: {...}, cloud: {...} },
//   hooks: { hooks: [...], interceptors: [...] },
//   responses: { processed: 42, errors: 0 }
// }
```

## Troubleshooting

### Common Issues

1. **OpenAI API errors**: Check API key and rate limits
2. **Supabase connection**: Verify credentials and network access
3. **SQLite initialization**: Ensure write permissions in data directory
4. **Memory overflow**: Adjust MAX_LOCAL_ITEMS in .env

### Logs

Check logs for detailed information:
```bash
tail -f logs/rag-system.log
```

## Advanced Features

### Custom Ranking Weights

```javascript
import memoryRanker from './src/memory/memory-ranker.js';

memoryRanker.updateWeights({
  similarity: 0.5,
  recency: 0.2,
  relevance: 0.15,
  importance: 0.1,
  success: 0.05
});
```

### Pattern Export/Import

```javascript
import patternStore from './src/patterns/pattern-store.js';

// Export patterns
const backup = await patternStore.export();

// Import patterns
await patternStore.import(backup);
```

## Contributing

Contributions are welcome! Please ensure:
- All tests pass
- Code follows existing patterns
- Documentation is updated

## License

MIT

## Support

For issues and questions, please refer to the documentation or create an issue in the repository.