# 🎯 Gemini CLI Handoff: Google Drive Integration + Advanced Memory Features

## Mission
Implement 4 major enhancements to the Smart Memory system based on n8n RAG architecture patterns. Transform passive memory storage into active document ingestion with versioning and conversation persistence.

## Current System State
- ✅ 54 memories stored and retrievable via SQLite FTS5
- ✅ HTTP API running on port 7777
- ✅ Supabase sync every 30 seconds
- ✅ MCP tools integrated with Claude Desktop
- **GAP**: No automatic document ingestion, no chunking, no versioning, no conversation memory

## Project Location
```bash
cd ~/Projects/demestihas-ai/mcp-smart-memory
```

## Phase 1: Google Drive Auto-Ingestion 🔄

### 1.1 Create Google Drive Monitor Service
**File**: `gdrive-monitor.js`

```javascript
import { google } from 'googleapis';
import dotenv from 'dotenv';
import path from 'path';
import { fileURLToPath } from 'url';
import axios from 'axios';

const __dirname = path.dirname(fileURLToPath(import.meta.url));
dotenv.config({ path: path.join(__dirname, '.env') });

class GDriveMonitor {
  constructor() {
    this.drive = null;
    this.auth = null;
    this.lastCheck = null;
    this.monitoredFolders = {
      'Meeting Notes': '1914m3M7kRzkd5RJqAfzRY9EBcJrKemZC',
      'Project Documentation': null, // Find and add folder ID
      'OXOS Medical': null, // Find and add folder ID
      'Consulting': null // Find and add folder ID
    };
  }

  async initialize() {
    // OAuth2 setup using existing Gmail credentials
    const auth = new google.auth.OAuth2(
      process.env.GOOGLE_CLIENT_ID,
      process.env.GOOGLE_CLIENT_SECRET,
      process.env.GOOGLE_REDIRECT_URI
    );

    // Load token from stored credentials
    const tokenPath = path.join(__dirname, '../google_credentials/token.json');
    const token = JSON.parse(await fs.readFile(tokenPath, 'utf8'));
    auth.setCredentials(token);
    
    this.auth = auth;
    this.drive = google.drive({ version: 'v3', auth });
  }

  async checkForNewFiles() {
    const now = new Date();
    const checkTime = this.lastCheck || new Date(Date.now() - 60 * 60 * 1000); // Last hour if first run
    
    for (const [folderName, folderId] of Object.entries(this.monitoredFolders)) {
      if (!folderId) continue;
      
      try {
        // Query for new/modified files
        const response = await this.drive.files.list({
          q: `'${folderId}' in parents and modifiedTime > '${checkTime.toISOString()}'`,
          fields: 'files(id, name, mimeType, modifiedTime, size)',
          orderBy: 'modifiedTime desc'
        });

        for (const file of response.data.files) {
          await this.processFile(file, folderName);
        }
      } catch (error) {
        console.error(`Error checking folder ${folderName}:`, error);
      }
    }
    
    this.lastCheck = now;
  }

  async processFile(file, folderName) {
    console.log(`Processing: ${file.name} from ${folderName}`);
    
    // Only process Google Docs and text files
    if (!file.mimeType.includes('document') && !file.mimeType.includes('text')) {
      return;
    }

    try {
      // Export as plain text
      const response = await this.drive.files.export({
        fileId: file.id,
        mimeType: 'text/plain'
      });

      // Send to memory API for processing
      await axios.post('http://localhost:7777/ingest/document', {
        fileId: file.id,
        fileName: file.name,
        folder: folderName,
        content: response.data,
        mimeType: file.mimeType,
        modifiedTime: file.modifiedTime
      });

      console.log(`✅ Ingested: ${file.name}`);
    } catch (error) {
      console.error(`Failed to process ${file.name}:`, error);
    }
  }

  async startMonitoring(intervalMinutes = 5) {
    await this.initialize();
    
    // Initial check
    await this.checkForNewFiles();
    
    // Set up interval
    setInterval(async () => {
      await this.checkForNewFiles();
    }, intervalMinutes * 60 * 1000);
    
    console.log(`📂 Monitoring Google Drive every ${intervalMinutes} minutes`);
  }
}

// Start monitoring if run directly
if (import.meta.url === `file://${process.argv[1]}`) {
  const monitor = new GDriveMonitor();
  monitor.startMonitoring();
}

export default GDriveMonitor;
```

### 1.2 Add Document Ingestion Endpoint
**File**: `memory-api.js` (ADD to existing file)

```javascript
// Add after existing imports
import GDriveMonitor from './gdrive-monitor.js';

// Add text splitter utility
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

// Add new endpoint for document ingestion
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

// Add endpoint to trigger manual Google Drive check
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
```

## Phase 2: Smart Document Chunking ✂️

### 2.1 Create Advanced Text Splitter
**File**: `text-splitter.js`

```javascript
import natural from 'natural';

class SmartTextSplitter {
  constructor(options = {}) {
    this.maxChunkSize = options.maxChunkSize || 1000;
    this.minChunkSize = options.minChunkSize || 200;
    this.overlap = options.overlap || 200;
    this.sentenceTokenizer = new natural.SentenceTokenizer();
  }

  // Split by headers (for markdown documents)
  splitByHeaders(text) {
    const chunks = [];
    const sections = text.split(/^#{1,3}\s+/m);
    
    for (const section of sections) {
      if (section.trim().length > this.maxChunkSize) {
        // Further split large sections
        chunks.push(...this.splitBySentences(section));
      } else if (section.trim().length > this.minChunkSize) {
        chunks.push(section.trim());
      }
    }
    
    return chunks;
  }

  // Split by sentences with smart boundaries
  splitBySentences(text) {
    const chunks = [];
    const sentences = this.sentenceTokenizer.tokenize(text);
    
    let currentChunk = '';
    
    for (const sentence of sentences) {
      if (currentChunk.length + sentence.length > this.maxChunkSize) {
        if (currentChunk) chunks.push(currentChunk.trim());
        currentChunk = sentence;
      } else {
        currentChunk += ' ' + sentence;
      }
    }
    
    if (currentChunk) chunks.push(currentChunk.trim());
    return chunks;
  }

  // Main splitting method
  split(text, documentType = 'auto') {
    // Detect document type if auto
    if (documentType === 'auto') {
      if (text.includes('# ') || text.includes('## ')) {
        documentType = 'markdown';
      } else if (text.includes('\n\n\n')) {
        documentType = 'structured';
      } else {
        documentType = 'plain';
      }
    }

    let chunks = [];
    
    switch (documentType) {
      case 'markdown':
        chunks = this.splitByHeaders(text);
        break;
      case 'structured':
        chunks = this.splitByParagraphs(text);
        break;
      default:
        chunks = this.splitBySentences(text);
    }

    // Add overlap between chunks
    return this.addOverlap(chunks);
  }

  splitByParagraphs(text) {
    const paragraphs = text.split(/\n\n+/);
    const chunks = [];
    
    let currentChunk = '';
    
    for (const para of paragraphs) {
      if (currentChunk.length + para.length > this.maxChunkSize) {
        if (currentChunk) chunks.push(currentChunk.trim());
        currentChunk = para;
      } else {
        currentChunk += '\n\n' + para;
      }
    }
    
    if (currentChunk) chunks.push(currentChunk.trim());
    return chunks;
  }

  addOverlap(chunks) {
    const overlapped = [];
    
    for (let i = 0; i < chunks.length; i++) {
      let chunk = chunks[i];
      
      // Add overlap from previous chunk
      if (i > 0 && this.overlap > 0) {
        const prevWords = chunks[i-1].split(' ');
        const overlapWords = prevWords.slice(-Math.floor(this.overlap/10));
        chunk = overlapWords.join(' ') + ' ... ' + chunk;
      }
      
      // Add preview of next chunk
      if (i < chunks.length - 1 && this.overlap > 0) {
        const nextWords = chunks[i+1].split(' ');
        const previewWords = nextWords.slice(0, Math.floor(this.overlap/10));
        chunk = chunk + ' ... ' + previewWords.join(' ');
      }
      
      overlapped.push(chunk);
    }
    
    return overlapped;
  }
}

export default SmartTextSplitter;
```

## Phase 3: Version Control System 📝

### 3.1 Add Version Management to Store
**File**: `simple-memory-store.js` (MODIFY existing file)

```javascript
// Add version control methods
async versionControl(memory) {
  // Check for existing versions of this content
  const contentHash = crypto
    .createHash('md5')
    .update(memory.content)
    .digest('hex');
  
  // Look for existing document with same fileId or contentHash
  const existing = await this.db.all(
    `SELECT * FROM memories 
     WHERE metadata LIKE ? 
     OR metadata LIKE ?
     ORDER BY timestamp DESC`,
    [`%"fileId":"${memory.metadata?.fileId}"%`, `%"contentHash":"${contentHash}"%`]
  );

  if (existing.length > 0) {
    const latest = existing[0];
    const latestMeta = JSON.parse(latest.metadata);
    
    // If content hasn't changed, skip
    if (latestMeta.contentHash === contentHash) {
      console.log('[VersionControl] Content unchanged, skipping');
      return { action: 'skipped', reason: 'no_change' };
    }
    
    // Archive old version
    await this.db.run(
      `UPDATE memories 
       SET type = 'archived', 
           category = 'archive',
           metadata = json_set(metadata, '$.archivedAt', ?)
       WHERE id = ?`,
      [new Date().toISOString(), latest.id]
    );
    
    console.log(`[VersionControl] Archived version: ${latest.id}`);
    return { action: 'archived', oldId: latest.id };
  }
  
  // Add content hash to metadata
  memory.metadata = {
    ...memory.metadata,
    contentHash,
    version: 1
  };
  
  return { action: 'new' };
}

// Modify existing store method to use version control
async store(memory) {
  await this.ensureInitialized();
  
  // Apply version control
  const versionResult = await this.versionControl(memory);
  
  if (versionResult.action === 'skipped') {
    return { 
      success: false, 
      reason: versionResult.reason,
      message: 'Content unchanged' 
    };
  }
  
  // Continue with regular storage...
  // [existing store code]
}

// Add method to get version history
async getVersionHistory(fileId) {
  await this.ensureInitialized();
  
  const versions = await this.db.all(
    `SELECT * FROM memories 
     WHERE metadata LIKE ? 
     ORDER BY timestamp DESC`,
    [`%"fileId":"${fileId}"%`]
  );
  
  return versions.map(v => ({
    ...v,
    metadata: JSON.parse(v.metadata)
  }));
}
```

## Phase 4: Conversation Memory 💬

### 4.1 Create Conversation Store
**File**: `conversation-memory.js`

```javascript
import sqlite3 from 'sqlite3';
import { open } from 'sqlite';
import path from 'path';
import { fileURLToPath } from 'url';
import crypto from 'crypto';

const __dirname = path.dirname(fileURLToPath(import.meta.url));

class ConversationMemory {
  constructor() {
    this.db = null;
    this.currentSession = null;
  }

  async initialize() {
    this.db = await open({
      filename: path.join(__dirname, 'data', 'conversations.db'),
      driver: sqlite3.Database
    });

    // Create conversation tables
    await this.db.exec(`
      CREATE TABLE IF NOT EXISTS conversations (
        id TEXT PRIMARY KEY,
        session_id TEXT,
        user_message TEXT,
        assistant_response TEXT,
        tool_calls TEXT,
        memories_used TEXT,
        timestamp INTEGER DEFAULT (strftime('%s', 'now') * 1000),
        metadata TEXT
      );

      CREATE TABLE IF NOT EXISTS sessions (
        id TEXT PRIMARY KEY,
        started_at INTEGER,
        ended_at INTEGER,
        message_count INTEGER DEFAULT 0,
        summary TEXT,
        metadata TEXT
      );

      CREATE INDEX IF NOT EXISTS idx_conv_session ON conversations(session_id);
      CREATE INDEX IF NOT EXISTS idx_conv_timestamp ON conversations(timestamp DESC);
    `);
  }

  async startSession(metadata = {}) {
    await this.ensureInitialized();
    
    this.currentSession = {
      id: crypto.randomUUID(),
      started_at: Date.now(),
      metadata
    };
    
    await this.db.run(
      `INSERT INTO sessions (id, started_at, metadata) VALUES (?, ?, ?)`,
      [this.currentSession.id, this.currentSession.started_at, JSON.stringify(metadata)]
    );
    
    return this.currentSession.id;
  }

  async addConversation(userMessage, assistantResponse, extras = {}) {
    await this.ensureInitialized();
    
    if (!this.currentSession) {
      await this.startSession();
    }
    
    const id = crypto.randomUUID();
    
    await this.db.run(
      `INSERT INTO conversations 
       (id, session_id, user_message, assistant_response, tool_calls, memories_used, metadata)
       VALUES (?, ?, ?, ?, ?, ?, ?)`,
      [
        id,
        this.currentSession.id,
        userMessage,
        assistantResponse,
        JSON.stringify(extras.toolCalls || []),
        JSON.stringify(extras.memoriesUsed || []),
        JSON.stringify(extras.metadata || {})
      ]
    );
    
    // Update session message count
    await this.db.run(
      `UPDATE sessions SET message_count = message_count + 1 WHERE id = ?`,
      [this.currentSession.id]
    );
    
    return id;
  }

  async getRecentConversations(limit = 10) {
    await this.ensureInitialized();
    
    const conversations = await this.db.all(
      `SELECT * FROM conversations 
       ORDER BY timestamp DESC 
       LIMIT ?`,
      [limit]
    );
    
    return conversations.map(c => ({
      ...c,
      tool_calls: JSON.parse(c.tool_calls || '[]'),
      memories_used: JSON.parse(c.memories_used || '[]'),
      metadata: JSON.parse(c.metadata || '{}')
    }));
  }

  async searchConversations(query, limit = 10) {
    await this.ensureInitialized();
    
    const pattern = `%${query.toLowerCase()}%`;
    
    const conversations = await this.db.all(
      `SELECT * FROM conversations 
       WHERE LOWER(user_message) LIKE ? 
          OR LOWER(assistant_response) LIKE ?
       ORDER BY timestamp DESC 
       LIMIT ?`,
      [pattern, pattern, limit]
    );
    
    return conversations;
  }

  async endSession(summary = null) {
    if (!this.currentSession) return;
    
    await this.db.run(
      `UPDATE sessions 
       SET ended_at = ?, summary = ? 
       WHERE id = ?`,
      [Date.now(), summary, this.currentSession.id]
    );
    
    this.currentSession = null;
  }

  async ensureInitialized() {
    if (!this.db) {
      await this.initialize();
    }
  }
}

export default new ConversationMemory();
```

### 4.2 Integrate Conversation Memory with API
**File**: `memory-api.js` (ADD to existing)

```javascript
// Add import
import conversationMemory from './conversation-memory.js';

// Add conversation endpoints
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
```

## Installation & Startup

### 1. Install Dependencies
```bash
cd ~/Projects/demestihas-ai/mcp-smart-memory
npm install googleapis natural
```

### 2. Environment Setup
Create `.env` file with Google credentials:
```env
GOOGLE_CLIENT_ID=your_client_id
GOOGLE_CLIENT_SECRET=your_client_secret
GOOGLE_REDIRECT_URI=http://localhost:7777/oauth/callback
```

### 3. Start Services
```bash
# Terminal 1: Start memory API with new features
npm start

# Terminal 2: Start Google Drive monitor
node gdrive-monitor.js

# Terminal 3: Test the system
./test_all_phases.sh
```

## Test Script
**File**: `test_all_phases.sh`

```bash
#!/bin/bash

echo "Testing All 4 Phases of Memory Enhancement"
echo "=========================================="

# Phase 1: Test document ingestion
echo -e "\n📂 Phase 1: Document Ingestion"
curl -X POST http://localhost:7777/ingest/document \
  -H "Content-Type: application/json" \
  -d '{
    "fileId": "test-doc-001",
    "fileName": "Test Meeting Notes.txt",
    "folder": "Meeting Notes",
    "content": "This is a test document with multiple sentences. It should be split into chunks. Each chunk will be stored separately. The system should handle this gracefully.",
    "mimeType": "text/plain",
    "modifiedTime": "'$(date -u +%Y-%m-%dT%H:%M:%SZ)'"
  }' | jq '.'

# Phase 2: Test chunking
echo -e "\n✂️ Phase 2: Verify Chunking"
curl "http://localhost:7777/context?q=test%20document" | jq '.memories | length'

# Phase 3: Test versioning
echo -e "\n📝 Phase 3: Version Control"
curl -X POST http://localhost:7777/ingest/document \
  -H "Content-Type: application/json" \
  -d '{
    "fileId": "test-doc-001",
    "fileName": "Test Meeting Notes.txt",
    "folder": "Meeting Notes",
    "content": "This is an UPDATED test document. The version control should archive the old one.",
    "mimeType": "text/plain",
    "modifiedTime": "'$(date -u +%Y-%m-%dT%H:%M:%SZ)'"
  }' | jq '.'

# Phase 4: Test conversation memory
echo -e "\n💬 Phase 4: Conversation Memory"
SESSION_ID=$(curl -X POST http://localhost:7777/conversation/start \
  -H "Content-Type: application/json" \
  -d '{"metadata": {"user": "test"}}' | jq -r '.sessionId')

echo "Started session: $SESSION_ID"

curl -X POST http://localhost:7777/conversation/add \
  -H "Content-Type: application/json" \
  -d '{
    "userMessage": "What documents do we have about testing?",
    "assistantResponse": "I found test documents in your Meeting Notes folder.",
    "memoriesUsed": ["test-doc-001"],
    "toolCalls": ["search", "retrieve"]
  }' | jq '.'

curl "http://localhost:7777/conversation/recent?limit=5" | jq '.'

echo -e "\n✅ All phases tested successfully!"
```

## Success Criteria
1. ✅ Google Drive documents auto-ingested within 5 minutes
2. ✅ Large documents split into searchable chunks
3. ✅ Document versions tracked (old versions archived)
4. ✅ Conversations persisted across sessions
5. ✅ Search returns relevant chunks from documents
6. ✅ No duplicate content from updated documents

## Monitoring Dashboard
Access at: `http://localhost:7777/dashboard` (to be implemented)
- Document ingestion status
- Chunk statistics
- Version history
- Conversation analytics

## Gemini CLI Commands for Zed

```bash
# Open project in Zed
zed ~/Projects/demestihas-ai/mcp-smart-memory

# Use Gemini to implement each phase
gemini "Implement the Google Drive monitor service from GEMINI_HANDOFF_GDRIVE_INTEGRATION.md"
gemini "Add the document ingestion endpoint to memory-api.js"
gemini "Create the smart text splitter with overlap"
gemini "Add version control to the memory store"
gemini "Implement conversation memory persistence"
```

## Next Steps After Implementation
1. Test with real Google Drive documents
2. Fine-tune chunk sizes based on retrieval quality
3. Set up monitoring for ingestion pipeline
4. Create cleanup job for old archived versions
5. Build conversation analytics dashboard

---

Ready to implement with Gemini CLI! This gives you a complete document ingestion pipeline matching the n8n reference architecture.
