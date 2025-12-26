#!/usr/bin/env node

import express from 'express';
import cors from 'cors';
import path from 'path';
import { fileURLToPath } from 'url';
import crypto from 'crypto';

const __dirname = path.dirname(fileURLToPath(import.meta.url));

// Import memory store adapters
import simpleMemoryStore from './simple-memory-store.js';
import ragMemoryAdapter from './rag-memory-adapter.js';
import hybridMemoryAdapter from './hybrid-memory-adapter.js';
import GDriveMonitor from './gdrive-monitor.js';
import conversationMemory from './conversation-memory.js';

// Use hybrid memory store (local SQLite + cloud sync to Supabase)
let memoryStore = hybridMemoryAdapter;
let contextRetriever, patternDetector;
let systemInitialized = false;

// Text splitter utility function
function splitText(text, maxChunkSize = 1000, overlap = 200) {
  const chunks = [];
  const sentences = text.match(/[^.!?]+[.!?]+/g) || [text];

  let currentChunk = '';
  let currentSize = 0;

  for (const sentence of sentences) {
    if (currentSize + sentence.length > maxChunkSize && currentChunk) {
      chunks.push(currentChunk.trim());
      // Keep last part for overlap
      const words = currentChunk.split(' ');
      const overlapWords = words.slice(-Math.floor(overlap/10));
      currentChunk = overlapWords.join(' ') + ' ' + sentence;
      currentSize = currentChunk.length;
    } else {
      currentChunk += ' ' + sentence;
      currentSize += sentence.length;
    }
  }

  if (currentChunk.trim()) {
    chunks.push(currentChunk.trim());
  }

  return chunks;
}

async function initializeMemorySystem() {
  try {
    // Initialize the memory store
    await memoryStore.initialize();
    console.log('[API] Memory system initialized successfully');

    // Set up context retriever using the active memory store
    contextRetriever = {
      getContext: async (query, options = {}) => {
        const memories = await memoryStore.search(query, options);
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

// Routes

// GET /health - System health and stats
app.get('/health', async (req, res) => {
  try {
    const stats = await memoryStore.getStats();

    res.json({
      status: 'healthy',
      initialized: systemInitialized,
      version: '2.0.0',
      uptime: process.uptime(),
      memory: {
        used: Math.round(process.memoryUsage().heapUsed / 1024 / 1024),
        total: Math.round(process.memoryUsage().heapTotal / 1024 / 1024)
      },
      stats: {
        ...stats,
        api_calls_today: 0 // Would track in production
      }
    });
  } catch (error) {
    res.status(500).json({
      status: 'error',
      error: error.message
    });
  }
});

// GET /context - Get relevant context for a query
app.get('/context', async (req, res) => {
  try {
    const { q: query, limit = 5 } = req.query;

    if (!query) {
      return res.status(400).json({
        error: 'Query parameter "q" is required'
      });
    }

    const context = await contextRetriever.getContext(query, {
      limit: parseInt(limit),
      includeFailures: true
    });

    // Format for easy copy/paste
    const formatted = {
      query,
      timestamp: new Date().toISOString(),
      memories: context.memories?.map(mem => ({
        id: mem.id,
        type: mem.type,
        content: mem.content,
        relevance: (mem.similarity * 100).toFixed(1) + '%',
        metadata: mem.metadata
      })) || [],
      patterns: context.patterns || [],
      formatted_text: context.memories?.map(mem =>
        `[${mem.type}] ${mem.content}`
      ).join('\n\n') || 'No relevant memories found'
    };

    res.json(formatted);
  } catch (error) {
    console.error('[API] Context error:', error);
    res.status(500).json({
      error: error.message
    });
  }
});

// POST /augment - Augment a prompt with context
app.post('/augment', async (req, res) => {
  try {
    const { prompt, max_context = 3 } = req.body;

    if (!prompt) {
      return res.status(400).json({
        error: 'Prompt is required'
      });
    }

    const context = await contextRetriever.getContext(prompt, {
      limit: max_context
    });

    let augmented = prompt;

    if (context.memories && context.memories.length > 0) {
      const contextText = context.memories
        .map(mem => `[${mem.type}] ${mem.content}`)
        .join('\n');

      augmented = `Context from memory:
${contextText}

Current request:
${prompt}`;
    }

    res.json({
      original_prompt: prompt,
      augmented_prompt: augmented,
      context_added: context.memories?.length || 0,
      timestamp: new Date().toISOString()
    });
  } catch (error) {
    console.error('[API] Augment error:', error);
    res.status(500).json({
      error: error.message
    });
  }
});

// POST /store - Store new memory
app.post('/store', async (req, res) => {
  try {
    const {
      content,
      type = 'note',
      metadata = {},
      importance = 'medium'
    } = req.body;

    if (!content) {
      return res.status(400).json({
        error: 'Content is required'
      });
    }

    const memory = {
      content,
      type,
      category: type,
      importance,
      metadata: {
        ...metadata,
        source: 'api',
        stored_at: new Date().toISOString()
      },
      projectId: 'mcp-smart-memory',
      userId: 'api-client'
    };

    const result = await memoryStore.store(memory);

    res.json({
      success: true,
      id: result.id,
      type,
      importance,
      timestamp: result.timestamp || Date.now(),
      message: 'Memory stored successfully'
    });
  } catch (error) {
    console.error('[API] Store error:', error);
    res.status(500).json({
      error: error.message
    });
  }
});

// POST /ingest/document - Document ingestion endpoint
app.post('/ingest/document', async (req, res) => {
  try {
    const {
      fileId,
      fileName,
      folder,
      content,
      mimeType,
      modifiedTime
    } = req.body;

    if (!content || !fileId) {
      return res.status(400).json({
        error: 'Content and fileId are required'
      });
    }

    // Check if document already exists (version control)
    const existing = await memoryStore.search(fileId, {
      type: 'document_metadata'
    });

    if (existing.length > 0) {
      // Archive old version
      for (const oldDoc of existing) {
        await memoryStore.store({
          content: oldDoc.content,
          type: 'document_archived',
          metadata: {
            ...oldDoc.metadata,
            archivedAt: new Date().toISOString(),
            replacedBy: fileId
          }
        });
        // Delete old version
        await memoryStore.deleteMemory(oldDoc.id);
      }
    }

    // Store document metadata
    await memoryStore.store({
      content: `Document: ${fileName}`,
      type: 'document_metadata',
      category: 'document',
      importance: 'high',
      metadata: {
        fileId,
        fileName,
        folder,
        mimeType,
        modifiedTime,
        totalLength: content.length,
        ingestedAt: new Date().toISOString()
      }
    });

    // Split content into chunks
    const chunks = splitText(content, 1000, 200);

    // Store each chunk
    for (let i = 0; i < chunks.length; i++) {
      await memoryStore.store({
        content: chunks[i],
        type: 'document_chunk',
        category: folder || 'document',
        importance: 'medium',
        metadata: {
          fileId,
          fileName,
          chunkIndex: i,
          totalChunks: chunks.length,
          folder,
          modifiedTime
        }
      });
    }

    res.json({
      success: true,
      fileId,
      fileName,
      chunksCreated: chunks.length,
      totalSize: content.length,
      message: `Document ingested as ${chunks.length} chunks`
    });

  } catch (error) {
    console.error('[API] Document ingestion error:', error);
    res.status(500).json({
      error: error.message
    });
  }
});

// POST /gdrive/check - Google Drive check endpoint
app.post('/gdrive/check', async (req, res) => {
  try {
    const monitor = new GDriveMonitor();
    await monitor.initialize();
    await monitor.checkForNewFiles();

    res.json({
      success: true,
      message: 'Google Drive check completed',
      timestamp: new Date().toISOString()
    });
  } catch (error) {
    console.error('[API] GDrive check error:', error);
    res.status(500).json({
      error: error.message
    });
  }
});

// Conversation endpoints
app.post('/conversation/start', async (req, res) => {
  try {
    const { metadata } = req.body;
    const sessionId = await conversationMemory.startSession(metadata);

    res.json({
      success: true,
      sessionId,
      message: 'Conversation session started'
    });
  } catch (error) {
    res.status(500).json({ error: error.message });
  }
});

app.post('/conversation/add', async (req, res) => {
  try {
    const {
      userMessage,
      assistantResponse,
      toolCalls,
      memoriesUsed,
      metadata
    } = req.body;

    const id = await conversationMemory.addConversation(
      userMessage,
      assistantResponse,
      { toolCalls, memoriesUsed, metadata }
    );

    res.json({
      success: true,
      conversationId: id,
      message: 'Conversation added'
    });
  } catch (error) {
    res.status(500).json({ error: error.message });
  }
});

app.get('/conversation/recent', async (req, res) => {
  try {
    const { limit = 10 } = req.query;
    const conversations = await conversationMemory.getRecentConversations(
      parseInt(limit)
    );

    res.json({
      conversations,
      count: conversations.length
    });
  } catch (error) {
    res.status(500).json({ error: error.message });
  }
});

app.get('/conversation/search', async (req, res) => {
  try {
    const { q: query, limit = 10 } = req.query;

    if (!query) {
      return res.status(400).json({ error: 'Query required' });
    }

    const conversations = await conversationMemory.searchConversations(
      query,
      parseInt(limit)
    );

    res.json({
      query,
      conversations,
      count: conversations.length
    });
  } catch (error) {
    res.status(500).json({ error: error.message });
  }
});

app.post('/conversation/end', async (req, res) => {
  try {
    const { summary } = req.body;
    await conversationMemory.endSession(summary);

    res.json({
      success: true,
      message: 'Session ended'
    });
  } catch (error) {
    res.status(500).json({ error: error.message });
  }
});

// GET /patterns - Find matching patterns
app.get('/patterns', async (req, res) => {
  try {
    const { q: query } = req.query;

    if (!query) {
      return res.status(400).json({
        error: 'Query parameter "q" is required'
      });
    }

    const patterns = await patternDetector.getPatterns(query);

    res.json({
      query,
      patterns: patterns || [],
      count: patterns?.length || 0,
      timestamp: new Date().toISOString()
    });
  } catch (error) {
    console.error('[API] Patterns error:', error);
    res.status(500).json({
      error: error.message
    });
  }
});

// POST /analyze - Analyze text for memorable content
app.post('/analyze', async (req, res) => {
  try {
    const { text, focus_areas = [] } = req.body;

    if (!text) {
      return res.status(400).json({
        error: 'Text is required'
      });
    }

    const findings = [];

    // Check each pattern
    for (const [category, pattern] of Object.entries(ANALYSIS_PATTERNS)) {
      if (focus_areas.length > 0 && !focus_areas.includes(category)) {
        continue;
      }

      const matches = text.match(pattern);
      if (matches) {
        matches.forEach(match => {
          let importance = 'medium';
          if (match.match(/critical|essential|important|must/i)) {
            importance = 'high';
          }

          findings.push({
            category,
            content: match.trim(),
            importance,
            start_index: text.indexOf(match),
            length: match.length
          });
        });
      }
    }

    // Deduplicate
    const unique = findings.reduce((acc, curr) => {
      const exists = acc.find(f => f.content === curr.content);
      if (!exists) acc.push(curr);
      return acc;
    }, []);

    res.json({
      text_length: text.length,
      findings: unique,
      count: unique.length,
      categories: [...new Set(unique.map(f => f.category))],
      has_valuable_content: unique.length > 0,
      timestamp: new Date().toISOString()
    });
  } catch (error) {
    console.error('[API] Analyze error:', error);
    res.status(500).json({
      error: error.message
    });
  }
});

// Error handling middleware
app.use((err, req, res, next) => {
  console.error('[API] Unhandled error:', err);
  res.status(500).json({
    error: 'Internal server error',
    message: err.message
  });
});

// 404 handler
app.use((req, res) => {
  res.status(404).json({
    error: 'Not found',
    available_endpoints: [
      'GET /health',
      'GET /context?q=query&limit=5',
      'POST /augment',
      'POST /store',
      'GET /patterns?q=query',
      'POST /analyze',
      'POST /ingest/document',
      'POST /gdrive/check',
      'POST /conversation/start',
      'POST /conversation/add',
      'GET /conversation/recent',
      'GET /conversation/search',
      'POST /conversation/end'
    ]
  });
});

// Start server
async function main() {
  const PORT = process.env.PORT || 7777;

  console.log('[API] Starting Memory API Server v2.0.0');

  // Initialize memory system
  await initializeMemorySystem();

  // Start Express server
  app.listen(PORT, () => {
    console.log(`[API] Server running on http://localhost:${PORT}`);
    console.log('[API] Available endpoints:');
    console.log('  - GET  /health           - System health and stats');
    console.log('  - GET  /context          - Get relevant context');
    console.log('  - POST /augment          - Augment prompt with context');
    console.log('  - POST /store            - Store new memory');
    console.log('  - GET  /patterns         - Find matching patterns');
    console.log('  - POST /analyze          - Analyze text for memorable content');
    console.log('  - POST /ingest/document  - Ingest and chunk documents');
    console.log('  - POST /gdrive/check     - Check Google Drive for new files');
    console.log('  - POST /conversation/*   - Conversation memory endpoints');
  });
}

main().catch((error) => {
  console.error('[API] Fatal error:', error);
  process.exit(1);
});
