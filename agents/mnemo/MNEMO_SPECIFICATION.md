# Mnemo Agent - Product Specification
## Agentic Memory Orchestration Layer

*Version: 1.0.0*  
*Last Updated: September 22, 2025*  
*Status: Design Phase*

---

## Executive Summary

**Mnemo** is an agentic memory orchestration layer that manages, optimizes, and intelligently routes between multiple memory systems. Unlike traditional memory stores, Mnemo is an active agent that understands context, learns patterns, and proactively surfaces relevant memories across different storage backends.

### Core Value Proposition
- **Unified Access**: Single interface to all memory types
- **Intelligent Routing**: Automatically selects optimal memory store
- **Active Learning**: Continuously improves memory relevance
- **Cross-Agent Coordination**: Shares context between all agents

---

## Problem Statement

### Current State Challenges
1. **Fragmented Memory Systems**
   - MCP Smart Memory (Port 7777) - Session patterns
   - EA-AI Memory - Active patterns
   - Google Drive - Document knowledge
   - Claude Conversation History - Past interactions
   - SQLite DBs - Local persistence
   - Redis Cache - Temporary state

2. **Lack of Orchestration**
   - No unified query interface
   - Manual memory type selection
   - No cross-memory correlation
   - Duplicate storage across systems
   - No memory lifecycle management

3. **Missing Intelligence**
   - No proactive memory surfacing
   - No pattern learning across stores
   - No memory importance ranking
   - No automatic consolidation

### Impact
- Agents can't share learned context effectively
- Manual memory management overhead
- Lost insights from memory fragmentation
- Reduced system learning capability

---

## Solution Architecture

### Mnemo as Meta-Memory Agent

```
┌─────────────────────────────────────────────────┐
│                   MNEMO AGENT                    │
│                                                   │
│  ┌──────────────────────────────────────────┐   │
│  │         Memory Type Classifier            │   │
│  └──────────────────────────────────────────┘   │
│                      │                           │
│  ┌──────────────────┴──────────────────────┐   │
│  │          Intelligent Router               │   │
│  └──────────────────┬──────────────────────┘   │
│                      │                           │
│  ┌─────────┬────────┼────────┬─────────────┐   │
│  ▼         ▼        ▼        ▼             ▼   │
│ Working  Episodic  Semantic  Pattern   External │
│ Memory   Memory    Memory    Memory    Memory   │
└─────────────────────────────────────────────────┘
                      │
     ┌───────┬────────┼────────┬────────┬────────┐
     ▼       ▼        ▼        ▼        ▼        ▼
  Redis  SQLite  Supabase  Google   Claude   Vector
  Cache   DBs    Cloud     Drive    History   Store
```

### Memory Types & Responsibilities

#### 1. Working Memory (Volatile)
- **Store**: Redis Cache
- **TTL**: 24 hours
- **Content**: Active session state, current context
- **Use Case**: Real-time operations, agent coordination

#### 2. Episodic Memory (Time-based)
- **Store**: SQLite + Timestamp indexes
- **TTL**: 90 days active, then archived
- **Content**: Events, interactions, completed tasks
- **Use Case**: "Remember when we...", timeline queries

#### 3. Semantic Memory (Knowledge)
- **Store**: Vector DB (Supabase pgvector)
- **TTL**: Permanent until invalidated
- **Content**: Facts, procedures, learned patterns
- **Use Case**: "How do I...", knowledge retrieval

#### 4. Pattern Memory (Behavioral)
- **Store**: MCP Smart Memory
- **TTL**: Updated on each occurrence
- **Content**: Workflows, preferences, habits
- **Use Case**: Automation, personalization

#### 5. External Memory (Documents)
- **Store**: Google Drive, Claude History
- **TTL**: User-managed
- **Content**: Documents, past conversations
- **Use Case**: Reference material, context retrieval

---

## Core Features

### 1. Unified Memory Interface

```javascript
// Single API for all memory operations
mnemo.remember(content, {
  type: 'auto',  // Auto-classify or specify
  importance: 'high',
  context: currentContext,
  ttl: '7d'
});

mnemo.recall(query, {
  types: ['all'],  // Or specific: ['semantic', 'episodic']
  timeRange: 'last_30d',
  includeExternal: true
});
```

### 2. Intelligent Classification

```javascript
// Mnemo automatically determines memory type
Input: "Fixed OAuth issue with redirect URL mismatch"
Output: {
  primary: 'semantic' (solution knowledge),
  secondary: 'episodic' (event that occurred),
  pattern: 'error_resolution'
}
```

### 3. Cross-Memory Correlation

```javascript
// Finds related memories across all stores
Query: "au pair schedule"
Returns:
  - Semantic: Scheduling rules, visa requirements
  - Episodic: Last week's schedule changes
  - Pattern: Typical scheduling conflicts
  - External: Google Doc with contract
  - Working: Today's active schedule
```

### 4. Proactive Memory Surfacing

```javascript
// Mnemo actively surfaces relevant memories
Trigger: User starts email about "project update"
Mnemo surfaces:
  - Last project status (episodic)
  - Project deadlines (semantic)
  - Typical update format (pattern)
  - Project documents (external)
```

### 5. Memory Lifecycle Management

```javascript
// Automatic promotion/demotion
Working Memory → Episodic (after session)
Episodic → Semantic (repeated access)
Semantic → Pattern (behavioral consistency)
All → Archive (based on decay function)
```

---

## Technical Implementation

### Phase 1: Core Infrastructure (Week 1)

#### Directory Structure
```
/agents/mnemo/
├── src/
│   ├── index.js                 # Main agent entry
│   ├── classifier.js            # Memory type classifier
│   ├── router.js               # Intelligent routing
│   ├── consolidator.js        # Cross-memory ops
│   └── lifecycle.js           # Memory management
├── adapters/
│   ├── redis-adapter.js       # Working memory
│   ├── sqlite-adapter.js      # Episodic memory
│   ├── vector-adapter.js      # Semantic memory
│   ├── mcp-adapter.js        # Pattern memory
│   └── external-adapter.js   # Drive/Claude
├── tests/
│   ├── classification.test.js
│   ├── routing.test.js
│   └── integration.test.js
├── config/
│   └── memory-config.json
├── Dockerfile
└── docker-compose.yml
```

#### API Endpoints
```javascript
POST   /remember      # Store new memory
GET    /recall        # Query memories
POST   /correlate     # Find relationships
GET    /surface       # Proactive suggestions
POST   /consolidate   # Merge duplicates
DELETE /forget        # Remove memory
GET    /stats         # Memory analytics
```

### Phase 2: Intelligence Layer (Week 2)

#### Classification Algorithm
```javascript
class MemoryClassifier {
  classify(content, context) {
    const features = this.extractFeatures(content);
    const scores = {
      working: this.scoreWorking(features, context),
      episodic: this.scoreEpisodic(features, context),
      semantic: this.scoreSemantic(features, context),
      pattern: this.scorePattern(features, context)
    };
    
    return {
      primary: this.getHighestScore(scores),
      secondary: this.getSecondaryTypes(scores),
      confidence: scores[primary] / 100
    };
  }
}
```

#### Relevance Ranking
```javascript
class RelevanceRanker {
  rank(memories, query, context) {
    return memories.map(memory => ({
      ...memory,
      relevance: this.calculateRelevance(memory, query, context),
      recency: this.recencyScore(memory.timestamp),
      frequency: this.accessFrequency(memory.id),
      importance: memory.metadata.importance
    })).sort((a, b) => 
      (a.relevance * 0.4 + 
       a.recency * 0.2 + 
       a.frequency * 0.2 + 
       a.importance * 0.2) -
      (b.relevance * 0.4 + 
       b.recency * 0.2 + 
       b.frequency * 0.2 + 
       b.importance * 0.2)
    );
  }
}
```

### Phase 3: Agent Integration (Week 3)

#### Inter-Agent Protocol
```javascript
// Mnemo provides memory context to other agents
class MnemoAgentInterface {
  // Called by Huata for calendar context
  async getCalendarContext(date) {
    return this.recall(`calendar events ${date}`, {
      types: ['episodic', 'pattern'],
      agents: ['huata']
    });
  }
  
  // Called by Lyco for task patterns
  async getTaskPatterns(taskType) {
    return this.recall(`task completion ${taskType}`, {
      types: ['pattern', 'semantic'],
      agents: ['lyco']
    });
  }
  
  // Called by Pluma for email context
  async getEmailContext(sender, subject) {
    return this.recall(`${sender} ${subject}`, {
      types: ['episodic', 'external'],
      agents: ['pluma']
    });
  }
}
```

---

## Integration Points

### Existing Systems

1. **MCP Smart Memory (Port 7777)**
   - Mnemo becomes primary interface
   - MCP continues as pattern store
   - Bidirectional sync for patterns

2. **EA-AI Bridge (Port 8081)**
   - Register Mnemo as available agent
   - Route memory queries to Mnemo
   - Share context between agents

3. **Redis Cache (Port 6379)**
   - Mnemo manages working memory
   - Sets TTL and eviction policies
   - Handles session state

4. **Google Drive**
   - Search via existing API
   - Cache document summaries
   - Link to source documents

5. **Claude Conversation History**
   - Use conversation_search tool
   - Extract key decisions/solutions
   - Build episodic timeline

### New Integrations

1. **Supabase Vector Store**
   - Setup pgvector extension
   - Create embeddings pipeline
   - Semantic similarity search

2. **Temporal Database**
   - SQLite with time-series optimization
   - Efficient episodic queries
   - Event correlation

---

## Success Metrics

### Quantitative
- **Query Latency**: < 200ms for 95% of queries
- **Relevance Score**: > 80% user satisfaction
- **Deduplication**: < 5% duplicate memories
- **Coverage**: 100% of memory sources accessible
- **Uptime**: 99.9% availability

### Qualitative
- Agents share context seamlessly
- Users don't repeat information
- System learns from interactions
- Proactive suggestions are helpful
- Memory feels "intelligent"

---

## Implementation Roadmap

### Week 1: Foundation
- [ ] Create Mnemo directory structure
- [ ] Build adapter interfaces
- [ ] Implement basic routing
- [ ] Setup Docker container
- [ ] Create health checks

### Week 2: Intelligence
- [ ] Build classification engine
- [ ] Implement relevance ranking
- [ ] Add correlation logic
- [ ] Create lifecycle manager
- [ ] Setup monitoring

### Week 3: Integration
- [ ] Connect to existing stores
- [ ] Implement agent interfaces
- [ ] Add proactive surfacing
- [ ] Create test suite
- [ ] Deploy to container

### Week 4: Optimization
- [ ] Performance tuning
- [ ] Add caching layer
- [ ] Implement analytics
- [ ] User feedback loop
- [ ] Documentation

---

## Test Plan

### Unit Tests
```javascript
describe('MemoryClassifier', () => {
  test('classifies solution as semantic');
  test('classifies event as episodic');
  test('identifies patterns from repetition');
  test('handles ambiguous content');
});

describe('Router', () => {
  test('routes to correct memory store');
  test('handles multi-store operations');
  test('manages failover scenarios');
});
```

### Integration Tests
```javascript
describe('Cross-Memory Operations', () => {
  test('correlates memories across stores');
  test('deduplicates similar memories');
  test('maintains consistency');
});

describe('Agent Communication', () => {
  test('provides context to Huata');
  test('shares patterns with Lyco');
  test('surfaces emails for Pluma');
});
```

### Performance Tests
- 1000 concurrent queries
- 10GB memory corpus
- Cross-store correlation
- Real-time classification

---

## Configuration

```json
{
  "mnemo": {
    "port": 8004,
    "memory_stores": {
      "working": {
        "type": "redis",
        "host": "localhost",
        "port": 6379,
        "ttl": "24h"
      },
      "episodic": {
        "type": "sqlite",
        "path": "/data/episodic.db",
        "retention": "90d"
      },
      "semantic": {
        "type": "vector",
        "url": "supabase://...",
        "dimension": 1536
      },
      "pattern": {
        "type": "mcp",
        "url": "http://localhost:7777"
      },
      "external": {
        "google_drive": true,
        "claude_history": true
      }
    },
    "intelligence": {
      "classification_threshold": 0.7,
      "relevance_weights": {
        "similarity": 0.4,
        "recency": 0.2,
        "frequency": 0.2,
        "importance": 0.2
      },
      "proactive_surfacing": true,
      "surface_threshold": 0.8
    },
    "lifecycle": {
      "promotion_threshold": 5,
      "archive_after": "90d",
      "consolidation_interval": "24h"
    }
  }
}
```

---

## Risk Mitigation

### Technical Risks
1. **Memory Store Failures**
   - Mitigation: Implement circuit breakers
   - Fallback: Cache recent queries

2. **Classification Errors**
   - Mitigation: Confidence thresholds
   - Fallback: Multi-type storage

3. **Performance Degradation**
   - Mitigation: Implement caching
   - Fallback: Direct store access

### Operational Risks
1. **Data Privacy**
   - All memories encrypted at rest
   - Access control per memory type
   - Audit logging for compliance

2. **Memory Bloat**
   - Automatic consolidation
   - Decay-based archival
   - Storage quotas per type

---

## Future Enhancements

### V2.0 Features
- **Emotional Context**: Track emotional states with memories
- **Causal Chains**: Link cause-effect relationships
- **Predictive Surfacing**: Anticipate needed memories
- **Memory Explanation**: Why this memory was surfaced
- **Collaborative Memory**: Shared team memories

### V3.0 Vision
- **Memory Synthesis**: Generate new insights from patterns
- **Temporal Reasoning**: Complex time-based queries
- **Counterfactual Memory**: "What if" scenarios
- **Memory Transfer**: Export/import memory sets
- **Federated Memory**: Distributed memory networks

---

## Conclusion

Mnemo transforms fragmented memory systems into an intelligent, unified memory layer that actively enhances every agent's capabilities. By treating memory as an active agent rather than passive storage, Mnemo enables true system-wide learning and adaptation.

**Next Steps:**
1. Review and approve specification
2. Allocate development resources
3. Begin Phase 1 implementation
4. Setup monitoring infrastructure
5. Plan integration timeline

---

*"Memory is not just storage—it's active intelligence."*