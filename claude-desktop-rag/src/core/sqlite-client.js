import sqlite3 from 'sqlite3';
import { promises as fs } from 'fs';
import { dirname } from 'path';
import winston from 'winston';
import { config } from '../../config/rag-config.js';

const logger = winston.createLogger({
  level: config.logging.level,
  format: winston.format.json(),
  transports: [
    new winston.transports.Console(),
    new winston.transports.File({ filename: config.logging.file })
  ]
});

class SQLiteClient {
  constructor() {
    this.db = null;
    this.initialized = false;
    this.syncQueue = [];
    this.syncTimer = null;
  }

  /**
   * Initialize SQLite database
   */
  async initialize() {
    if (this.initialized) return;

    try {
      // Ensure directory exists
      const dbDir = dirname(config.database.sqlitePath);
      await fs.mkdir(dbDir, { recursive: true });

      // Open database
      await new Promise((resolve, reject) => {
        this.db = new sqlite3.Database(config.database.sqlitePath, (err) => {
          if (err) reject(err);
          else resolve();
        });
      });

      // Enable foreign keys and WAL mode for better concurrency
      await this.run('PRAGMA foreign_keys = ON');
      await this.run('PRAGMA journal_mode = WAL');

      // Load schema
      const schemaPath = new URL('../../config/sqlite-schema.sql', import.meta.url);
      const schema = await fs.readFile(schemaPath, 'utf-8');
      
      // Execute schema statements
      const statements = schema.split(';').filter(s => s.trim());
      for (const statement of statements) {
        if (statement.trim()) {
          await this.run(statement);
        }
      }

      this.initialized = true;
      logger.info('SQLite database initialized successfully');

      // Start periodic pruning
      this.startPruning();
    } catch (error) {
      logger.error('Failed to initialize SQLite database', { error: error.message });
      throw error;
    }
  }

  /**
   * Store memory locally
   */
  async storeMemory(memory) {
    await this.ensureInitialized();

    const sql = `
      INSERT INTO project_memories_cache (
        id, project_id, content, embedding_json, metadata,
        interaction_type, tool_chain, file_paths, success_score,
        created_at, session_id, user_id
      ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    `;

    const params = [
      memory.id,
      memory.project_id || config.project.id,
      memory.content,
      JSON.stringify(memory.embedding),
      JSON.stringify(memory.metadata || {}),
      memory.interaction_type,
      JSON.stringify(memory.tool_chain || []),
      JSON.stringify(memory.file_paths || []),
      memory.success_score || 1.0,
      Math.floor(Date.now() / 1000),
      memory.session_id,
      memory.user_id
    ];

    try {
      await this.run(sql, params);
      logger.debug('Memory stored locally', { id: memory.id });

      // Add to sync queue
      this.addToSyncQueue('project_memories', memory.id, 'INSERT', memory);

      return memory;
    } catch (error) {
      logger.error('Failed to store memory locally', { error: error.message });
      throw error;
    }
  }

  /**
   * Search memories locally
   */
  async searchMemories(embedding, options = {}) {
    await this.ensureInitialized();

    const {
      limit = config.rag.maxContextItems,
      projectId = config.project.id
    } = options;

    // Since SQLite doesn't have native vector support,
    // we'll fetch candidates and calculate similarity in JS
    const sql = `
      SELECT id, content, embedding_json, metadata, created_at,
             file_paths, tool_chain, success_score, last_accessed
      FROM project_memories_cache
      WHERE project_id = ?
      ORDER BY created_at DESC
      LIMIT ?
    `;

    try {
      const rows = await this.all(sql, [projectId, limit * 3]); // Fetch more for filtering

      // Calculate similarities
      const results = rows.map(row => {
        const rowEmbedding = JSON.parse(row.embedding_json);
        const similarity = this.cosineSimilarity(embedding, rowEmbedding);
        
        return {
          ...row,
          embedding: rowEmbedding,
          metadata: JSON.parse(row.metadata || '{}'),
          file_paths: JSON.parse(row.file_paths || '[]'),
          tool_chain: JSON.parse(row.tool_chain || '[]'),
          similarity
        };
      });

      // Filter by threshold and sort by similarity
      const filtered = results
        .filter(r => r.similarity >= config.rag.similarityThreshold)
        .sort((a, b) => b.similarity - a.similarity)
        .slice(0, limit);

      // Update last accessed
      for (const result of filtered) {
        await this.run(
          'UPDATE project_memories_cache SET last_accessed = ? WHERE id = ?',
          [Math.floor(Date.now() / 1000), result.id]
        );
      }

      logger.debug('Memories searched locally', { count: filtered.length });
      return filtered;
    } catch (error) {
      logger.error('Failed to search memories locally', { error: error.message });
      return [];
    }
  }

  /**
   * Store pattern locally
   */
  async storePattern(pattern) {
    await this.ensureInitialized();

    const sql = `
      INSERT OR REPLACE INTO workflow_patterns_cache (
        id, pattern_hash, pattern_name, trigger_embedding_json,
        action_sequence, occurrence_count, success_rate,
        last_used, project_contexts, auto_apply
      ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    `;

    const params = [
      pattern.id,
      pattern.pattern_hash,
      pattern.pattern_name,
      JSON.stringify(pattern.trigger_embedding),
      JSON.stringify(pattern.action_sequence),
      pattern.occurrence_count || 1,
      pattern.success_rate || 1.0,
      Math.floor(Date.now() / 1000),
      JSON.stringify(pattern.project_contexts || []),
      pattern.auto_apply ? 1 : 0
    ];

    try {
      await this.run(sql, params);
      logger.debug('Pattern stored locally', { id: pattern.id });

      // Add to sync queue
      this.addToSyncQueue('workflow_patterns', pattern.id, 'UPSERT', pattern);

      return pattern;
    } catch (error) {
      logger.error('Failed to store pattern locally', { error: error.message });
      throw error;
    }
  }

  /**
   * Cache embedding
   */
  async cacheEmbedding(textHash, embedding, model) {
    await this.ensureInitialized();

    const sql = `
      INSERT OR REPLACE INTO embedding_cache (
        text_hash, embedding_json, model, created_at, last_accessed
      ) VALUES (?, ?, ?, ?, ?)
    `;

    const now = Math.floor(Date.now() / 1000);
    
    try {
      await this.run(sql, [
        textHash,
        JSON.stringify(embedding),
        model,
        now,
        now
      ]);
    } catch (error) {
      logger.warn('Failed to cache embedding', { error: error.message });
    }
  }

  /**
   * Get cached embedding
   */
  async getCachedEmbedding(textHash) {
    await this.ensureInitialized();

    const sql = `
      SELECT embedding_json FROM embedding_cache
      WHERE text_hash = ?
        AND created_at > ?
    `;

    const cutoff = Math.floor(Date.now() / 1000) - config.openai.cacheTTL;

    try {
      const row = await this.get(sql, [textHash, cutoff]);
      
      if (row) {
        // Update access stats
        await this.run(
          'UPDATE embedding_cache SET accessed_count = accessed_count + 1, last_accessed = ? WHERE text_hash = ?',
          [Math.floor(Date.now() / 1000), textHash]
        );
        
        return JSON.parse(row.embedding_json);
      }
    } catch (error) {
      logger.warn('Failed to get cached embedding', { error: error.message });
    }

    return null;
  }

  /**
   * Add to sync queue
   */
  addToSyncQueue(tableName, recordId, operation, payload) {
    const sql = `
      INSERT INTO sync_queue (table_name, record_id, operation, payload)
      VALUES (?, ?, ?, ?)
    `;

    this.run(sql, [
      tableName,
      recordId,
      operation,
      JSON.stringify(payload)
    ]).catch(error => {
      logger.warn('Failed to add to sync queue', { error: error.message });
    });
  }

  /**
   * Get pending sync items
   */
  async getSyncQueue(limit = 50) {
    await this.ensureInitialized();

    const sql = `
      SELECT * FROM sync_queue
      WHERE status = 'pending'
      ORDER BY created_at
      LIMIT ?
    `;

    try {
      return await this.all(sql, [limit]);
    } catch (error) {
      logger.error('Failed to get sync queue', { error: error.message });
      return [];
    }
  }

  /**
   * Mark sync item as completed
   */
  async markSyncCompleted(id) {
    await this.ensureInitialized();

    const sql = `
      UPDATE sync_queue
      SET status = 'completed'
      WHERE id = ?
    `;

    try {
      await this.run(sql, [id]);
    } catch (error) {
      logger.warn('Failed to mark sync completed', { error: error.message });
    }
  }

  /**
   * Prune old data
   */
  async pruneOldData() {
    await this.ensureInitialized();

    const cutoff = Math.floor(Date.now() / 1000) - (config.database.cacheTTLHours * 3600);

    try {
      // Prune old memories
      const memoriesResult = await this.run(
        'DELETE FROM project_memories_cache WHERE created_at < ? AND synced_to_cloud = 1',
        [cutoff]
      );

      // Prune old embeddings
      const embeddingsResult = await this.run(
        'DELETE FROM embedding_cache WHERE last_accessed < ?',
        [cutoff]
      );

      // Prune completed sync items
      await this.run(
        "DELETE FROM sync_queue WHERE status = 'completed' AND created_at < ?",
        [cutoff - 86400] // Keep for 1 day after completion
      );

      // Enforce max items limit
      const countResult = await this.get('SELECT COUNT(*) as count FROM project_memories_cache');
      
      if (countResult.count > config.database.maxLocalItems) {
        const excess = countResult.count - config.database.maxLocalItems;
        await this.run(`
          DELETE FROM project_memories_cache
          WHERE id IN (
            SELECT id FROM project_memories_cache
            WHERE synced_to_cloud = 1
            ORDER BY last_accessed
            LIMIT ?
          )
        `, [excess]);
      }

      logger.info('Pruned old data from local cache');
    } catch (error) {
      logger.error('Failed to prune old data', { error: error.message });
    }
  }

  /**
   * Start periodic pruning
   */
  startPruning() {
    setInterval(() => {
      this.pruneOldData();
    }, config.performance.pruneIntervalMs);
  }

  /**
   * Calculate cosine similarity
   */
  cosineSimilarity(embedding1, embedding2) {
    if (!embedding1 || !embedding2) return 0;
    if (embedding1.length !== embedding2.length) return 0;

    let dotProduct = 0;
    let norm1 = 0;
    let norm2 = 0;

    for (let i = 0; i < embedding1.length; i++) {
      dotProduct += embedding1[i] * embedding2[i];
      norm1 += embedding1[i] * embedding1[i];
      norm2 += embedding2[i] * embedding2[i];
    }

    norm1 = Math.sqrt(norm1);
    norm2 = Math.sqrt(norm2);

    if (norm1 === 0 || norm2 === 0) return 0;
    
    return dotProduct / (norm1 * norm2);
  }

  /**
   * Database helper methods
   */
  async run(sql, params = []) {
    return new Promise((resolve, reject) => {
      this.db.run(sql, params, function(err) {
        if (err) reject(err);
        else resolve({ lastID: this.lastID, changes: this.changes });
      });
    });
  }

  async get(sql, params = []) {
    return new Promise((resolve, reject) => {
      this.db.get(sql, params, (err, row) => {
        if (err) reject(err);
        else resolve(row);
      });
    });
  }

  async all(sql, params = []) {
    return new Promise((resolve, reject) => {
      this.db.all(sql, params, (err, rows) => {
        if (err) reject(err);
        else resolve(rows);
      });
    });
  }

  /**
   * Ensure database is initialized
   */
  async ensureInitialized() {
    if (!this.initialized) {
      await this.initialize();
    }
  }

  /**
   * Get database statistics
   */
  async getStats() {
    await this.ensureInitialized();

    try {
      const [memories, patterns, embeddings, syncQueue] = await Promise.all([
        this.get('SELECT COUNT(*) as count FROM project_memories_cache'),
        this.get('SELECT COUNT(*) as count FROM workflow_patterns_cache'),
        this.get('SELECT COUNT(*) as count FROM embedding_cache'),
        this.get('SELECT COUNT(*) as count FROM sync_queue WHERE status = "pending"')
      ]);

      return {
        memories: memories.count || 0,
        patterns: patterns.count || 0,
        embeddings: embeddings.count || 0,
        pendingSync: syncQueue.count || 0
      };
    } catch (error) {
      logger.error('Failed to get SQLite stats', { error: error.message });
      return { memories: 0, patterns: 0, embeddings: 0, pendingSync: 0 };
    }
  }

  /**
   * Close database connection
   */
  async close() {
    if (this.db) {
      return new Promise((resolve, reject) => {
        this.db.close((err) => {
          if (err) reject(err);
          else {
            this.initialized = false;
            resolve();
          }
        });
      });
    }
  }
}

export default new SQLiteClient();