#!/usr/bin/env node

import express from 'express';
import cors from 'cors';
import path from 'path';
import { fileURLToPath } from 'url';
import crypto from 'crypto';

const __dirname = path.dirname(fileURLToPath(import.meta.url));

// Import enhanced memory store with vector support
import SimpleMemoryStore from './simple-memory-store-vector.js';

// Initialize memory store
const memoryStore = new SimpleMemoryStore();
let contextRetriever, patternDetector;
let systemInitialized = false;

async function initializeMemorySystem() {
  try {
    // Initialize the memory store
    await memoryStore.initialize();
    console.log('[API] Memory system initialized successfully');

    // Set up context retriever using the active memory store
    contextRetriever = {
      getContext: async (query, options = {}) => {
        const memories = await memoryStore.searchHybrid(query, options);
        return {
          query,
          memories,
          patterns: [],
          timestamp: Date.now()
        };
      }
    };

    // Simple pattern detector
    patternDetector = {
      detectPattern: async (actions) => ({
        id: crypto.randomUUID(),
        pattern: actions.join(' -> '),
        confidence: 0.8,
        occurrences: 3
      }),
      getPatterns: async (query) => []
    };

    systemInitialized = true;
    return true;
  } catch (error) {
    console.error('[API] Failed to initialize memory system:', error.message);
    throw error;
  }
}

// Create Express app
const app = express();

// Middleware
app.use(cors({
  origin: '*', // Allow all origins for browser extensions
  methods: ['GET', 'POST', 'OPTIONS'],
  allowedHeaders: ['Content-Type', 'Authorization']
}));
app.use(express.json({ limit: '10mb' }));

// Request logging middleware
app.use((req, res, next) => {
  console.log(`[API] ${req.method} ${req.path}`);
  next();
});

// Analysis patterns (same as MCP server)
const ANALYSIS_PATTERNS = {
  solution: /(?:fixed|solved|solution|resolved|worked)[\s\S]{0,200}/gi,
  configuration: /(?:config|setting|path|url|endpoint|token|key)[\s\S]{0,200}/gi,
  discovery: /(?:discovered|found|realized|learned|turns out)[\s\S]{0,200}/gi,
  decision: /(?:decided|chose|selected|will use|going with)[\s\S]{0,200}/gi,
  error_fix: /(?:error|failed|issue|problem|bug)[\s\S]{0,200}(?:fixed|solved|resolved)/gi
};

// Helper function to explain search results
function explainResults(results, mode) {
  if (results.length === 0) return 'No matches found';

  const sources = [...new Set(results.flatMap(r => r.sources || []))];

  if (mode === 'hybrid' && sources.length > 1) {
    return `Found matches using both semantic similarity and keyword matching`;
  } else if (mode === 'semantic') {
    return `Showing conceptually similar content (even without exact keywords)`;
  } else {
    return `Showing keyword matches`;
  }
}

// Routes

// GET /health - System health and stats
app.get('/health', async (req, res) => {
  try {
    const stats = await memoryStore.getStats();

    res.json({
      status: 'healthy',
      initialized: systemInitialized,
      version: '2.1.0',
      features: {
        vectorSearch: stats.vectorSearchEnabled || false,
        semanticSearch: stats.vectorSearchEnabled || false,
        hybridSearch: stats.vectorSearchEnabled || false,
        fts5Search: true
      },
      uptime: process.uptime(),
      memory: {
        used: Math.round(process.memoryUsage().heapUsed / 1024 / 1024),
        total: Math.round(process.memoryUsage().heapTotal / 1024 / 1024)
      },
      stats
    });
  } catch (error) {
    console.error('[API] Health check failed:', error);
    res.status(503).json({
      status: 'unhealthy',
      error: error.message,
      initialized: systemInitialized
    });
  }
});

// POST /memory - Store a new memory
app.post('/memory', async (req, res) => {
  try {
    const { content, type, category, importance, metadata } = req.body;

    if (!content) {
      return res.status(400).json({ error: 'Content is required' });
    }

    // Auto-categorize if not provided
    const detectedType = type || detectMemoryType(content);
    const finalCategory = category || detectedType || 'general';
    const finalImportance = importance || determineImportance(content);

    const memory = {
      content,
      type: detectedType,
      category: finalCategory,
      importance: finalImportance,
      metadata: metadata || extractMetadata(content),
      timestamp: Date.now()
    };

    // Use storeWithVector to ensure embedding is generated
    const result = await memoryStore.storeWithVector(memory);

    res.json({
      success: true,
      id: result.id,
      type: detectedType,
      category: finalCategory,
      importance: finalImportance,
      timestamp: result.timestamp
    });
  } catch (error) {
    console.error('[API] Memory storage error:', error);
    res.status(500).json({ error: error.message });
  }
});

// GET /search - Unified search endpoint with multiple modes
app.get('/search', async (req, res) => {
  try {
    const {
      q: query,
      limit = 10,
      mode = 'hybrid', // hybrid | semantic | keyword
      semanticWeight = 0.7,
      threshold = 0.7
    } = req.query;

    if (!query) {
      return res.status(400).json({ error: 'Query required' });
    }

    let results;
    const searchOptions = {
      limit: parseInt(limit),
      threshold: parseFloat(threshold)
    };

    switch(mode) {
      case 'semantic':
        results = await memoryStore.searchSemantic(query, searchOptions);
        break;
      case 'keyword':
        results = await memoryStore.search(query, searchOptions); // existing FTS5
        break;
      default: // hybrid
        results = await memoryStore.searchHybrid(query, {
          ...searchOptions,
          weights: {
            semantic: parseFloat(semanticWeight),
            keyword: 1 - parseFloat(semanticWeight)
          }
        });
    }

    res.json({
      query,
      mode,
      results,
      count: results.length,
      explanation: explainResults(results, mode)
    });
  } catch (error) {
    console.error('[API] Search error:', error);
    res.status(500).json({ error: error.message });
  }
});

// GET /search/semantic - Semantic search endpoint
app.get('/search/semantic', async (req, res) => {
  try {
    const { q: query, limit = 10, threshold = 0.7 } = req.query;

    if (!query) {
      return res.status(400).json({ error: 'Query required' });
    }

    const results = await memoryStore.searchSemantic(query, {
      limit: parseInt(limit),
      threshold: parseFloat(threshold)
    });

    res.json({
      query,
      type: 'semantic',
      results,
      count: results.length,
      explanation: 'Showing conceptually similar memories'
    });
  } catch (error) {
    console.error('[API] Semantic search error:', error);
    res.status(500).json({ error: error.message });
  }
});

// GET /search/hybrid - Hybrid search endpoint
app.get('/search/hybrid', async (req, res) => {
  try {
    const {
      q: query,
      limit = 10,
      semanticWeight = 0.7
    } = req.query;

    if (!query) {
      return res.status(400).json({ error: 'Query required' });
    }

    const results = await memoryStore.searchHybrid(query, {
      limit: parseInt(limit),
      weights: {
        semantic: parseFloat(semanticWeight),
        keyword: 1 - parseFloat(semanticWeight)
      }
    });

    res.json({
      query,
      type: 'hybrid',
      results,
      count: results.length,
      weights: {
        semantic: parseFloat(semanticWeight),
        keyword: 1 - parseFloat(semanticWeight)
      },
      explanation: explainResults(results, 'hybrid')
    });
  } catch (error) {
    console.error('[API] Hybrid search error:', error);
    res.status(500).json({ error: error.message });
  }
});

// GET /context - Get contextual memories
app.get('/context', async (req, res) => {
  try {
    const { q: query, limit = 10, mode = 'hybrid' } = req.query;

    if (!query) {
      return res.status(400).json({ error: 'Query required' });
    }

    const context = await contextRetriever.getContext(query, { limit: parseInt(limit), mode });

    res.json({
      query,
      context: context.memories,
      patterns: context.patterns,
      count: context.memories.length,
      mode
    });
  } catch (error) {
    console.error('[API] Context retrieval error:', error);
    res.status(500).json({ error: error.message });
  }
});

// GET /memories - List all memories
app.get('/memories', async (req, res) => {
  try {
    const { limit = 100, type } = req.query;

    const memories = await memoryStore.getAll({
      limit: parseInt(limit),
      type
    });

    res.json({
      memories,
      count: memories.length,
      total: (await memoryStore.getStats()).totalMemories
    });
  } catch (error) {
    console.error('[API] List memories error:', error);
    res.status(500).json({ error: error.message });
  }
});

// DELETE /memory/:id - Delete a specific memory
app.delete('/memory/:id', async (req, res) => {
  try {
    const { id } = req.params;

    const result = await memoryStore.deleteMemory(id);

    if (result.success) {
      res.json({ success: true, message: 'Memory deleted' });
    } else {
      res.status(404).json({ error: 'Memory not found' });
    }
  } catch (error) {
    console.error('[API] Delete memory error:', error);
    res.status(500).json({ error: error.message });
  }
});

// Helper functions
function detectMemoryType(content) {
  for (const [type, pattern] of Object.entries(ANALYSIS_PATTERNS)) {
    if (pattern.test(content)) {
      return type;
    }
  }
  return 'note';
}

function determineImportance(content) {
  const lowPriorityWords = ['maybe', 'possibly', 'minor', 'small', 'trivial'];
  const highPriorityWords = ['critical', 'important', 'urgent', 'major', 'significant', 'bug', 'error', 'failed'];

  const contentLower = content.toLowerCase();

  if (highPriorityWords.some(word => contentLower.includes(word))) {
    return 'high';
  }

  if (lowPriorityWords.some(word => contentLower.includes(word))) {
    return 'low';
  }

  return 'medium';
}

function extractMetadata(content) {
  const metadata = {};

  // Extract URLs
  const urlMatch = content.match(/https?:\/\/[^\s]+/gi);
  if (urlMatch) {
    metadata.urls = urlMatch;
  }

  // Extract file paths
  const pathMatch = content.match(/[\.\/\\][\w\/\\.-]+\.\w+/g);
  if (pathMatch) {
    metadata.files = pathMatch;
  }

  // Extract code snippets (basic detection)
  const codeMatch = content.match(/```[\s\S]*?```/g);
  if (codeMatch) {
    metadata.hasCode = true;
    metadata.codeBlocks = codeMatch.length;
  }

  return metadata;
}

// Start server
const PORT = process.env.PORT || 7777;

async function startServer() {
  try {
    await initializeMemorySystem();

    app.listen(PORT, '0.0.0.0', () => {
      console.log(`
╔════════════════════════════════════════════════╗
║         Smart Memory API Server v2.1.0        ║
║                                                ║
║  Status: RUNNING                               ║
║  Port: ${PORT}                                ║
║  Features:                                     ║
║    ✅ Vector Search (Semantic)                ║
║    ✅ Hybrid Search (Semantic + Keyword)      ║
║    ✅ FTS5 Full-Text Search                   ║
║    ✅ Supabase Cloud Sync                     ║
║                                                ║
║  Endpoints:                                    ║
║    GET  /health          - System status      ║
║    POST /memory          - Store memory       ║
║    GET  /search          - Unified search     ║
║    GET  /search/semantic - Semantic only      ║
║    GET  /search/hybrid   - Hybrid search      ║
║    GET  /context         - Get context        ║
║    GET  /memories        - List all           ║
║    DELETE /memory/:id    - Delete memory      ║
║                                                ║
║  Ready to store and retrieve memories!        ║
╚════════════════════════════════════════════════╝
      `);
    });
  } catch (error) {
    console.error('[API] Failed to start server:', error);
    process.exit(1);
  }
}

// Handle shutdown gracefully
process.on('SIGINT', async () => {
  console.log('\n[API] Shutting down gracefully...');
  if (memoryStore && memoryStore.close) {
    await memoryStore.close();
  }
  process.exit(0);
});

// Start the server
startServer();
