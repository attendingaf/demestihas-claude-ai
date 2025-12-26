import sqlite3 from 'sqlite3';
import { open } from 'sqlite';
import path from 'path';
import { fileURLToPath } from 'url';
import crypto from 'crypto';
import fs from 'fs/promises';
import { createClient } from '@supabase/supabase-js';
import OpenAI from 'openai';
import { config } from 'dotenv';

const __dirname = path.dirname(fileURLToPath(import.meta.url));
config({ path: path.join(__dirname, '.env') });

class SimpleMemoryStore {
  constructor() {
    this.db = null;
    this.initialized = false;

    // Initialize Supabase if credentials are available
    if (process.env.SUPABASE_URL && process.env.SUPABASE_ANON_KEY) {
      this.supabase = createClient(
        process.env.SUPABASE_URL,
        process.env.SUPABASE_ANON_KEY
      );
      console.error('[SimpleMemoryStore] Supabase client initialized');
    } else {
      console.error('[SimpleMemoryStore] Supabase credentials not found, vector search disabled');
    }

    // Initialize OpenAI if API key is available
    if (process.env.OPENAI_API_KEY) {
      this.openai = new OpenAI({
        apiKey: process.env.OPENAI_API_KEY
      });
      console.error('[SimpleMemoryStore] OpenAI client initialized');
    } else {
      console.error('[SimpleMemoryStore] OpenAI API key not found, embedding generation disabled');
    }
  }

  async initialize() {
    if (this.initialized) return;

    try {
      // Create data directory if it doesn't exist
      const dataDir = path.join(__dirname, 'data');
      await fs.mkdir(dataDir, { recursive: true });

      // Open SQLite database
      this.db = await open({
        filename: path.join(dataDir, 'smart_memory.db'),
        driver: sqlite3.Database
      });

      // Create memories table with full-text search
      await this.db.exec(`
        CREATE TABLE IF NOT EXISTS memories (
          id TEXT PRIMARY KEY,
          content TEXT NOT NULL,
          type TEXT DEFAULT 'note',
          category TEXT,
          importance TEXT DEFAULT 'medium',
          metadata TEXT,
          timestamp INTEGER DEFAULT (strftime('%s', 'now') * 1000),
          project_id TEXT,
          user_id TEXT
        );

        CREATE INDEX IF NOT EXISTS idx_memories_type ON memories(type);
        CREATE INDEX IF NOT EXISTS idx_memories_category ON memories(category);
        CREATE INDEX IF NOT EXISTS idx_memories_timestamp ON memories(timestamp DESC);
        CREATE INDEX IF NOT EXISTS idx_memories_importance ON memories(importance);

        -- Create full-text search virtual table
        CREATE VIRTUAL TABLE IF NOT EXISTS memories_fts USING fts5(
          id UNINDEXED,
          content,
          type,
          category,
          metadata,
          content=memories,
          content_rowid=rowid
        );

        -- Create triggers to keep FTS in sync
        CREATE TRIGGER IF NOT EXISTS memories_ai AFTER INSERT ON memories BEGIN
          INSERT INTO memories_fts(rowid, id, content, type, category, metadata)
          VALUES (new.rowid, new.id, new.content, new.type, new.category, new.metadata);
        END;

        CREATE TRIGGER IF NOT EXISTS memories_ad AFTER DELETE ON memories BEGIN
          DELETE FROM memories_fts WHERE rowid = old.rowid;
        END;

        CREATE TRIGGER IF NOT EXISTS memories_au AFTER UPDATE ON memories BEGIN
          DELETE FROM memories_fts WHERE rowid = old.rowid;
          INSERT INTO memories_fts(rowid, id, content, type, category, metadata)
          VALUES (new.rowid, new.id, new.content, new.type, new.category, new.metadata);
        END;
      `);

      this.initialized = true;
      console.error('[SimpleMemoryStore] Initialized successfully');
    } catch (error) {
      console.error('[SimpleMemoryStore] Initialization failed:', error);
      throw error;
    }
  }

  async ensureInitialized() {
    if (!this.initialized) {
      await this.initialize();
    }
  }

  async generateEmbedding(text) {
    if (!this.openai) {
      console.error('[SimpleMemoryStore] OpenAI not configured, skipping embedding generation');
      return null;
    }

    try {
      const response = await this.openai.embeddings.create({
        model: 'text-embedding-3-small',
        input: text.substring(0, 8000), // Respect token limits
        dimensions: 1536
      });
      return response.data[0].embedding;
    } catch (error) {
      console.error('[SimpleMemoryStore] Embedding generation failed:', error);
      return null;
    }
  }

  async store(memory) {
    await this.ensureInitialized();

    const id = memory.id || crypto.randomUUID();
    const timestamp = memory.timestamp || Date.now();
    const metadata = typeof memory.metadata === 'object'
      ? JSON.stringify(memory.metadata)
      : memory.metadata || '{}';

    try {
      // Store in SQLite first
      await this.db.run(
        `INSERT INTO memories (id, content, type, category, importance, metadata, timestamp, project_id, user_id)
         VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)`,
        [
          id,
          memory.content,
          memory.type || 'note',
          memory.category || memory.type || 'general',
          memory.importance || 'medium',
          metadata,
          timestamp,
          memory.projectId || 'mcp-smart-memory',
          memory.userId || 'claude-desktop'
        ]
      );

      console.error(`[SimpleMemoryStore] Stored memory in SQLite: ${id}`);

      // Generate embedding and store in Supabase if available
      if (this.supabase && this.openai) {
        const embedding = await this.generateEmbedding(memory.content);
        if (embedding) {
          await this.syncToSupabase({
            id,
            content: memory.content,
            embedding,
            metadata: JSON.parse(metadata),
            category: memory.category || memory.type || 'general',
            importance: memory.importance || 'medium',
            timestamp
          });
        }
      }

      return { success: true, id, timestamp };
    } catch (error) {
      console.error('[SimpleMemoryStore] Store failed:', error);
      throw error;
    }
  }

  async storeWithVector(memory) {
    // Generate embedding if not provided
    if (!memory.embedding && memory.content && this.openai) {
      memory.embedding = await this.generateEmbedding(memory.content);
    }

    // Store locally with existing method
    const result = await this.store(memory);

    // The store method already handles Supabase sync
    return result;
  }

  async syncToSupabase(memory) {
    if (!this.supabase) return;

    try {
      const { error } = await this.supabase
        .from('memories')
        .upsert({
          id: memory.id,
          content: memory.content,
          embedding: memory.embedding,
          metadata: memory.metadata,
          category: memory.category,
          importance: memory.importance,
          timestamp: memory.timestamp
        });

      if (error) {
        console.error('[SimpleMemoryStore] Supabase sync error:', error);
      } else {
        console.error(`[SimpleMemoryStore] Synced to Supabase: ${memory.id}`);
      }
    } catch (error) {
      console.error('[SimpleMemoryStore] Supabase sync failed:', error);
    }
  }

  async searchSemantic(query, options = {}) {
    const { limit = 10, threshold = 0.7 } = options;

    if (!this.supabase || !this.openai) {
      console.error('[SimpleMemoryStore] Semantic search not available, falling back to FTS');
      return this.search(query, options);
    }

    try {
      // Generate query embedding
      const queryEmbedding = await this.generateEmbedding(query);

      if (!queryEmbedding) {
        console.error('[SimpleMemoryStore] Failed to generate query embedding, falling back to FTS');
        return this.search(query, options);
      }

      // Search in Supabase using vector similarity
      const { data, error } = await this.supabase
        .rpc('search_memories_semantic', {
          query_embedding: queryEmbedding,
          match_count: limit,
          similarity_threshold: threshold
        });

      if (error) {
        console.error('[SimpleMemoryStore] Semantic search error:', error);
        // Fallback to FTS5
        return this.search(query, options);
      }

      console.error(`[SimpleMemoryStore] Semantic search found ${data?.length || 0} results`);
      return data || [];
    } catch (error) {
      console.error('[SimpleMemoryStore] Semantic search failed:', error);
      return this.search(query, options);
    }
  }

  async searchHybrid(query, options = {}) {
    const { limit = 10, weights = { semantic: 0.7, keyword: 0.3 } } = options;

    // Run both searches in parallel
    const [semantic, keyword] = await Promise.all([
      this.searchSemantic(query, { limit: limit * 2 }),
      this.search(query, { limit: limit * 2 }) // existing FTS5
    ]);

    // Merge and re-rank results
    const merged = this.mergeResults(semantic, keyword, weights);

    console.error(`[SimpleMemoryStore] Hybrid search merged ${merged.length} results`);
    return merged.slice(0, limit);
  }

  mergeResults(semantic, keyword, weights) {
    const scoreMap = new Map();

    // Add semantic results
    semantic.forEach(result => {
      const id = result.id;
      scoreMap.set(id, {
        ...result,
        finalScore: (result.similarity || 0) * weights.semantic,
        sources: ['semantic']
      });
    });

    // Merge keyword results
    keyword.forEach(result => {
      const id = result.id;
      if (scoreMap.has(id)) {
        // Combine scores if in both
        const existing = scoreMap.get(id);
        existing.finalScore += (result.similarity || result.score || 0.5) * weights.keyword;
        existing.sources.push('keyword');
      } else {
        // Add keyword-only results
        scoreMap.set(id, {
          ...result,
          finalScore: (result.similarity || result.score || 0.5) * weights.keyword,
          sources: ['keyword']
        });
      }
    });

    // Sort by final score
    return Array.from(scoreMap.values())
      .sort((a, b) => b.finalScore - a.finalScore);
  }

  async search(query, options = {}) {
    await this.ensureInitialized();

    const {
      limit = 10,
      type = null,
      includeFailures = true,
      threshold = 0 // Not used for text search, but kept for compatibility
    } = options;

    try {
      // Clean and prepare search query
      const searchTerms = query
        .toLowerCase()
        .replace(/[^\w\s]/g, ' ')
        .split(/\s+/)
        .filter(term => term.length > 2)
        .join(' OR ');

      // Build SQL query with FTS5
      let sql = `
        SELECT
          m.*,
          bm25(memories_fts, 0, 1.0, 2.0, 1.5, 1.5) as rank
        FROM memories m
        JOIN memories_fts ON m.rowid = memories_fts.rowid
        WHERE memories_fts MATCH ?
      `;

      const params = [searchTerms];

      // Add type filter if specified
      if (type) {
        sql += ' AND m.type = ?';
        params.push(type);
      }

      // Filter out failures if requested
      if (!includeFailures) {
        sql += ' AND m.type != "error_fix"';
      }

      // Order by relevance and recency
      sql += ' ORDER BY rank, m.timestamp DESC LIMIT ?';
      params.push(limit);

      const results = await this.db.all(sql, params);

      // Format results with similarity scores (based on rank)
      const formatted = results.map(row => ({
        id: row.id,
        content: row.content,
        type: row.type,
        category: row.category,
        importance: row.importance,
        metadata: row.metadata ? JSON.parse(row.metadata) : {},
        timestamp: row.timestamp,
        similarity: Math.min(1, Math.max(0, 1 - (row.rank / -10))), // Convert BM25 to 0-1 score
        score: Math.min(1, Math.max(0, 1 - (row.rank / -10))) // Also include as score
      }));

      console.error(`[SimpleMemoryStore] FTS5 search found ${formatted.length} results for: ${query}`);
      return formatted;
    } catch (error) {
      console.error('[SimpleMemoryStore] Search failed:', error);

      // Fallback to simple LIKE search if FTS fails
      try {
        const fallbackSql = `
          SELECT * FROM memories
          WHERE LOWER(content) LIKE ?
             OR LOWER(type) LIKE ?
             OR LOWER(category) LIKE ?
             OR LOWER(metadata) LIKE ?
          ORDER BY timestamp DESC
          LIMIT ?
        `;

        const searchPattern = `%${query.toLowerCase()}%`;
        const results = await this.db.all(fallbackSql, [
          searchPattern, searchPattern, searchPattern, searchPattern, limit
        ]);

        return results.map(row => ({
          ...row,
          metadata: row.metadata ? JSON.parse(row.metadata) : {},
          similarity: 0.5, // Default similarity for LIKE matches
          score: 0.5
        }));
      } catch (fallbackError) {
        console.error('[SimpleMemoryStore] Fallback search also failed:', fallbackError);
        return [];
      }
    }
  }

  async getAll(options = {}) {
    await this.ensureInitialized();

    const { limit = 100, type = null } = options;

    try {
      let sql = 'SELECT * FROM memories';
      const params = [];

      if (type) {
        sql += ' WHERE type = ?';
        params.push(type);
      }

      sql += ' ORDER BY timestamp DESC LIMIT ?';
      params.push(limit);

      const results = await this.db.all(sql, params);

      return results.map(row => ({
        ...row,
        metadata: row.metadata ? JSON.parse(row.metadata) : {}
      }));
    } catch (error) {
      console.error('[SimpleMemoryStore] GetAll failed:', error);
      return [];
    }
  }

  async getStats() {
    await this.ensureInitialized();

    try {
      const stats = await this.db.get(`
        SELECT
          COUNT(*) as total,
          COUNT(DISTINCT type) as types,
          COUNT(DISTINCT category) as categories
        FROM memories
      `);

      const typeBreakdown = await this.db.all(`
        SELECT type, COUNT(*) as count
        FROM memories
        GROUP BY type
      `);

      const recentCount = await this.db.get(`
        SELECT COUNT(*) as recent
        FROM memories
        WHERE timestamp > ?
      `, [Date.now() - 24 * 60 * 60 * 1000]); // Last 24 hours

      return {
        totalMemories: stats.total,
        uniqueTypes: stats.types,
        uniqueCategories: stats.categories,
        memoryTypes: typeBreakdown.reduce((acc, row) => {
          acc[row.type] = row.count;
          return acc;
        }, {}),
        recentMemories: recentCount.recent,
        lastUpdated: Date.now(),
        vectorSearchEnabled: !!(this.supabase && this.openai)
      };
    } catch (error) {
      console.error('[SimpleMemoryStore] GetStats failed:', error);
      return {
        totalMemories: 0,
        uniqueTypes: 0,
        uniqueCategories: 0,
        memoryTypes: {},
        recentMemories: 0,
        vectorSearchEnabled: false
      };
    }
  }

  async deleteMemory(id) {
    await this.ensureInitialized();

    try {
      const result = await this.db.run('DELETE FROM memories WHERE id = ?', [id]);

      // Also delete from Supabase if available
      if (this.supabase) {
        await this.supabase
          .from('memories')
          .delete()
          .eq('id', id);
      }

      return { success: result.changes > 0 };
    } catch (error) {
      console.error('[SimpleMemoryStore] Delete failed:', error);
      return { success: false };
    }
  }

  async close() {
    if (this.db) {
      await this.db.close();
      this.initialized = false;
    }
  }
}

export default SimpleMemoryStore;
