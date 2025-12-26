import sqlite3 from 'sqlite3';
import { open } from 'sqlite';
import { promises as fs } from 'fs';
import { dirname } from 'path';
import winston from 'winston';
import crypto from 'crypto';
import { config } from '../../config/rag-config.js';

const logger = winston.createLogger({
  level: config.logging.level,
  format: winston.format.json(),
  transports: [
    new winston.transports.Console(),
    new winston.transports.File({ filename: config.logging.file })
  ]
});

class LRUCache {
  constructor(maxSize = 100) {
    this.maxSize = maxSize;
    this.cache = new Map();
    this.hits = 0;
    this.misses = 0;
  }

  get(key) {
    if (this.cache.has(key)) {
      const value = this.cache.get(key);
      this.cache.delete(key);
      this.cache.set(key, value);
      this.hits++;
      return value;
    }
    this.misses++;
    return null;
  }

  set(key, value) {
    if (this.cache.has(key)) {
      this.cache.delete(key);
    } else if (this.cache.size >= this.maxSize) {
      const firstKey = this.cache.keys().next().value;
      this.cache.delete(firstKey);
    }
    this.cache.set(key, value);
  }

  getStats() {
    const total = this.hits + this.misses;
    return {
      hits: this.hits,
      misses: this.misses,
      hitRate: total > 0 ? (this.hits / total) : 0,
      size: this.cache.size
    };
  }

  clear() {
    this.cache.clear();
    this.hits = 0;
    this.misses = 0;
  }
}

class OptimizedSQLiteClient {
  constructor() {
    this.db = null;
    this.initialized = false;
    this.syncQueue = [];
    this.syncTimer = null;
    
    // LRU caches for different query types
    this.queryCache = new LRUCache(100);
    this.embeddingCache = new LRUCache(200);
    this.searchCache = new LRUCache(50);
    
    // Pre-computed embeddings for frequent queries
    this.precomputedEmbeddings = new Map();
    
    // Performance metrics
    this.metrics = {
      retrievalTimes: [],
      cacheHitRate: 0,
      avgRetrievalTime: 0
    };
  }

  async initialize() {
    if (this.initialized) return;

    try {
      const dbDir = dirname(config.database.sqlitePath);
      await fs.mkdir(dbDir, { recursive: true });

      // Open database with optimized settings
      this.db = await open({
        filename: config.database.sqlitePath,
        driver: sqlite3.Database
      });

      // Enable memory-mapped I/O for faster reads
      await this.db.exec('PRAGMA mmap_size = 268435456'); // 256MB memory map
      
      // Optimize for speed
      await this.db.exec('PRAGMA journal_mode = WAL');
      await this.db.exec('PRAGMA synchronous = NORMAL');
      await this.db.exec('PRAGMA cache_size = -64000'); // 64MB cache
      await this.db.exec('PRAGMA temp_store = MEMORY');
      await this.db.exec('PRAGMA page_size = 4096');
      await this.db.exec('PRAGMA foreign_keys = ON');
      
      // Enable query planner optimizations
      await this.db.exec('PRAGMA optimize');
      await this.db.exec('PRAGMA analysis_limit = 1000');

      // Load existing schema
      const schemaPath = new URL('../../config/sqlite-schema.sql', import.meta.url);
      const schema = await fs.readFile(schemaPath, 'utf-8');
      
      const statements = schema.split(';').filter(s => s.trim());
      for (const statement of statements) {
        if (statement.trim()) {
          await this.db.exec(statement);
        }
      }

      // Add new context cache table
      await this.db.exec(`
        CREATE TABLE IF NOT EXISTS context_cache (
          query_hash TEXT PRIMARY KEY,
          embedding BLOB,
          results TEXT,
          hit_count INTEGER DEFAULT 1,
          last_accessed INTEGER DEFAULT (strftime('%s', 'now'))
        );
        
        CREATE INDEX IF NOT EXISTS idx_cache_access ON context_cache(last_accessed DESC);
        CREATE INDEX IF NOT EXISTS idx_cache_hits ON context_cache(hit_count DESC);
        
        -- Additional optimization indexes
        CREATE INDEX IF NOT EXISTS idx_memories_project_created 
          ON project_memories_cache(project_id, created_at DESC);
        CREATE INDEX IF NOT EXISTS idx_memories_accessed 
          ON project_memories_cache(last_accessed DESC);
        CREATE INDEX IF NOT EXISTS idx_embeddings_hash_model 
          ON embedding_cache(text_hash, model);
      `);

      this.initialized = true;
      logger.info('Optimized SQLite database initialized successfully');

      // Start periodic tasks
      this.startPruning();
      this.startPrecomputing();
      this.startMetricsReporting();
      
    } catch (error) {
      logger.error('Failed to initialize optimized SQLite database', { error: error.message });
      throw error;
    }
  }

  async storeMemory(memory) {
    await this.ensureInitialized();
    const startTime = Date.now();

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
      await this.db.run(sql, params);
      
      // Invalidate related caches
      this.invalidateSearchCache(memory.project_id);
      
      // Add to sync queue
      this.addToSyncQueue('project_memories', memory.id, 'INSERT', memory);
      
      // Track performance
      this.trackRetrievalTime(Date.now() - startTime);
      
      logger.debug('Memory stored locally', { 
        id: memory.id, 
        time: Date.now() - startTime 
      });

      return memory;
    } catch (error) {
      logger.error('Failed to store memory locally', { error: error.message });
      throw error;
    }
  }

  async searchMemories(embedding, options = {}) {
    await this.ensureInitialized();
    const startTime = Date.now();

    const {
      limit = config.rag.maxContextItems,
      projectId = config.project.id,
      contextBoost = 1.0
    } = options;

    // Generate cache key
    const cacheKey = this.generateCacheKey(embedding, projectId, limit, contextBoost);
    
    // Check search cache first
    const cached = this.searchCache.get(cacheKey);
    if (cached) {
      this.trackRetrievalTime(Date.now() - startTime);
      logger.debug('Search results from cache', { 
        time: Date.now() - startTime,
        cacheHit: true 
      });
      return cached;
    }

    // Check context cache in database
    const contextCached = await this.getContextCache(cacheKey);
    if (contextCached) {
      this.searchCache.set(cacheKey, contextCached);
      this.trackRetrievalTime(Date.now() - startTime);
      logger.debug('Search results from context cache', { 
        time: Date.now() - startTime,
        contextCacheHit: true 
      });
      return contextCached;
    }

    // Perform actual search with optimized query
    const sql = `
      SELECT id, content, embedding_json, metadata, created_at,
             file_paths, tool_chain, success_score, last_accessed
      FROM project_memories_cache
      WHERE project_id = ?
      ORDER BY last_accessed DESC, created_at DESC
      LIMIT ?
    `;

    try {
      const rows = await this.db.all(sql, [projectId, limit * 3]);

      // Parallel similarity calculation
      const results = await Promise.all(rows.map(async row => {
        const rowEmbedding = JSON.parse(row.embedding_json);
        const similarity = this.cosineSimilarity(embedding, rowEmbedding);
        
        return {
          ...row,
          embedding: rowEmbedding,
          metadata: JSON.parse(row.metadata || '{}'),
          file_paths: JSON.parse(row.file_paths || '[]'),
          tool_chain: JSON.parse(row.tool_chain || '[]'),
          similarity: similarity * contextBoost
        };
      }));

      // Filter and sort
      const filtered = results
        .filter(r => r.similarity >= config.rag.similarityThreshold)
        .sort((a, b) => b.similarity - a.similarity)
        .slice(0, limit);

      // Batch update last accessed
      if (filtered.length > 0) {
        const updateTime = Math.floor(Date.now() / 1000);
        const updateSql = `
          UPDATE project_memories_cache 
          SET last_accessed = ? 
          WHERE id IN (${filtered.map(() => '?').join(',')})
        `;
        await this.db.run(updateSql, [updateTime, ...filtered.map(r => r.id)]);
      }

      // Cache the results
      this.searchCache.set(cacheKey, filtered);
      await this.storeContextCache(cacheKey, embedding, filtered);

      // Track performance
      const retrievalTime = Date.now() - startTime;
      this.trackRetrievalTime(retrievalTime);
      
      logger.debug('Memories searched locally', { 
        count: filtered.length,
        time: retrievalTime,
        cacheHit: false
      });
      
      return filtered;
    } catch (error) {
      logger.error('Failed to search memories locally', { error: error.message });
      return [];
    }
  }

  async storeContextCache(queryHash, embedding, results) {
    const sql = `
      INSERT OR REPLACE INTO context_cache (
        query_hash, embedding, results, hit_count, last_accessed
      ) VALUES (?, ?, ?, 
        COALESCE((SELECT hit_count FROM context_cache WHERE query_hash = ?), 0) + 1,
        strftime('%s', 'now')
      )
    `;

    try {
      await this.db.run(sql, [
        queryHash,
        Buffer.from(new Float32Array(embedding).buffer),
        JSON.stringify(results),
        queryHash
      ]);
    } catch (error) {
      logger.warn('Failed to store context cache', { error: error.message });
    }
  }

  async getContextCache(queryHash) {
    const sql = `
      SELECT results FROM context_cache
      WHERE query_hash = ?
        AND last_accessed > ?
    `;

    const cutoff = Math.floor(Date.now() / 1000) - 3600; // 1 hour cache

    try {
      const row = await this.db.get(sql, [queryHash, cutoff]);
      
      if (row) {
        // Update cache stats
        await this.db.run(
          'UPDATE context_cache SET hit_count = hit_count + 1, last_accessed = strftime("%s", "now") WHERE query_hash = ?',
          [queryHash]
        );
        
        return JSON.parse(row.results);
      }
    } catch (error) {
      logger.warn('Failed to get context cache', { error: error.message });
    }

    return null;
  }

  generateCacheKey(...args) {
    const hash = crypto.createHash('sha256');
    args.forEach(arg => {
      if (Array.isArray(arg)) {
        hash.update(JSON.stringify(arg));
      } else if (typeof arg === 'object') {
        hash.update(JSON.stringify(arg));
      } else {
        hash.update(String(arg));
      }
    });
    return hash.digest('hex');
  }

  invalidateSearchCache(projectId) {
    // Clear project-specific cache entries
    for (const [key, value] of this.searchCache.cache.entries()) {
      if (key.includes(projectId)) {
        this.searchCache.cache.delete(key);
      }
    }
  }

  async precomputeFrequentQueries() {
    const sql = `
      SELECT query_hash, embedding, hit_count
      FROM context_cache
      WHERE hit_count > 3
      ORDER BY hit_count DESC, last_accessed DESC
      LIMIT 20
    `;

    try {
      const rows = await this.db.all(sql);
      
      for (const row of rows) {
        const embedding = new Float32Array(row.embedding.buffer);
        this.precomputedEmbeddings.set(row.query_hash, embedding);
      }
      
      logger.debug('Precomputed frequent query embeddings', { 
        count: rows.length 
      });
    } catch (error) {
      logger.warn('Failed to precompute embeddings', { error: error.message });
    }
  }

  trackRetrievalTime(time) {
    this.metrics.retrievalTimes.push(time);
    
    // Keep only last 100 times
    if (this.metrics.retrievalTimes.length > 100) {
      this.metrics.retrievalTimes.shift();
    }
    
    // Calculate average
    this.metrics.avgRetrievalTime = 
      this.metrics.retrievalTimes.reduce((a, b) => a + b, 0) / 
      this.metrics.retrievalTimes.length;
    
    // Calculate cache hit rate
    const searchStats = this.searchCache.getStats();
    const queryStats = this.queryCache.getStats();
    const embeddingStats = this.embeddingCache.getStats();
    
    const totalHits = searchStats.hits + queryStats.hits + embeddingStats.hits;
    const totalRequests = totalHits + searchStats.misses + queryStats.misses + embeddingStats.misses;
    
    this.metrics.cacheHitRate = totalRequests > 0 ? (totalHits / totalRequests) : 0;
  }

  async getPerformanceMetrics() {
    await this.ensureInitialized();
    
    const dbStats = await this.getStats();
    const cacheStats = {
      search: this.searchCache.getStats(),
      query: this.queryCache.getStats(),
      embedding: this.embeddingCache.getStats()
    };
    
    return {
      avgRetrievalTime: this.metrics.avgRetrievalTime,
      cacheHitRate: this.metrics.cacheHitRate,
      recentRetrievals: this.metrics.retrievalTimes.slice(-10),
      cacheStats,
      dbStats,
      precomputedCount: this.precomputedEmbeddings.size
    };
  }

  startPrecomputing() {
    // Precompute every 5 minutes
    setInterval(() => {
      this.precomputeFrequentQueries();
    }, 5 * 60 * 1000);
    
    // Initial precompute
    setTimeout(() => {
      this.precomputeFrequentQueries();
    }, 5000);
  }

  startMetricsReporting() {
    // Report metrics every minute
    setInterval(async () => {
      const metrics = await this.getPerformanceMetrics();
      
      if (metrics.avgRetrievalTime > 100) {
        logger.warn('Retrieval time exceeding target', { 
          avg: metrics.avgRetrievalTime 
        });
      }
      
      if (metrics.cacheHitRate < 0.8 && this.metrics.retrievalTimes.length > 50) {
        logger.info('Cache hit rate below target', { 
          rate: metrics.cacheHitRate 
        });
      }
      
      logger.debug('Performance metrics', metrics);
    }, 60 * 1000);
  }

  // Include all other methods from original SQLiteClient...
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
      await this.db.run(sql, params);
      logger.debug('Pattern stored locally', { id: pattern.id });
      this.addToSyncQueue('workflow_patterns', pattern.id, 'UPSERT', pattern);
      return pattern;
    } catch (error) {
      logger.error('Failed to store pattern locally', { error: error.message });
      throw error;
    }
  }

  async cacheEmbedding(textHash, embedding, model) {
    await this.ensureInitialized();

    // Use LRU cache first
    this.embeddingCache.set(textHash, embedding);

    const sql = `
      INSERT OR REPLACE INTO embedding_cache (
        text_hash, embedding_json, model, created_at, last_accessed
      ) VALUES (?, ?, ?, ?, ?)
    `;

    const now = Math.floor(Date.now() / 1000);
    
    try {
      await this.db.run(sql, [
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

  async getCachedEmbedding(textHash) {
    // Check LRU cache first
    const cached = this.embeddingCache.get(textHash);
    if (cached) return cached;

    await this.ensureInitialized();

    const sql = `
      SELECT embedding_json FROM embedding_cache
      WHERE text_hash = ?
        AND created_at > ?
    `;

    const cutoff = Math.floor(Date.now() / 1000) - config.openai.cacheTTL;

    try {
      const row = await this.db.get(sql, [textHash, cutoff]);
      
      if (row) {
        await this.db.run(
          'UPDATE embedding_cache SET accessed_count = accessed_count + 1, last_accessed = ? WHERE text_hash = ?',
          [Math.floor(Date.now() / 1000), textHash]
        );
        
        const embedding = JSON.parse(row.embedding_json);
        this.embeddingCache.set(textHash, embedding);
        return embedding;
      }
    } catch (error) {
      logger.warn('Failed to get cached embedding', { error: error.message });
    }

    return null;
  }

  addToSyncQueue(tableName, recordId, operation, payload) {
    const sql = `
      INSERT INTO sync_queue (table_name, record_id, operation, payload)
      VALUES (?, ?, ?, ?)
    `;

    this.db.run(sql, [
      tableName,
      recordId,
      operation,
      JSON.stringify(payload)
    ]).catch(error => {
      logger.warn('Failed to add to sync queue', { error: error.message });
    });
  }

  async getSyncQueue(limit = 50) {
    await this.ensureInitialized();

    const sql = `
      SELECT * FROM sync_queue
      WHERE status = 'pending'
      ORDER BY created_at
      LIMIT ?
    `;

    try {
      return await this.db.all(sql, [limit]);
    } catch (error) {
      logger.error('Failed to get sync queue', { error: error.message });
      return [];
    }
  }

  async markSyncCompleted(id) {
    await this.ensureInitialized();

    const sql = `
      UPDATE sync_queue
      SET status = 'completed'
      WHERE id = ?
    `;

    try {
      await this.db.run(sql, [id]);
    } catch (error) {
      logger.warn('Failed to mark sync completed', { error: error.message });
    }
  }

  async pruneOldData() {
    await this.ensureInitialized();

    const cutoff = Math.floor(Date.now() / 1000) - (config.database.cacheTTLHours * 3600);

    try {
      // Prune old context cache
      await this.db.run(
        'DELETE FROM context_cache WHERE last_accessed < ? AND hit_count < 3',
        [cutoff]
      );

      // Prune old memories
      await this.db.run(
        'DELETE FROM project_memories_cache WHERE created_at < ? AND synced_to_cloud = 1',
        [cutoff]
      );

      // Prune old embeddings
      await this.db.run(
        'DELETE FROM embedding_cache WHERE last_accessed < ?',
        [cutoff]
      );

      // Prune completed sync items
      await this.db.run(
        "DELETE FROM sync_queue WHERE status = 'completed' AND created_at < ?",
        [cutoff - 86400]
      );

      // Enforce max items limit
      const countResult = await this.db.get('SELECT COUNT(*) as count FROM project_memories_cache');
      
      if (countResult.count > config.database.maxLocalItems) {
        const excess = countResult.count - config.database.maxLocalItems;
        await this.db.run(`
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

  startPruning() {
    setInterval(() => {
      this.pruneOldData();
    }, config.performance.pruneIntervalMs);
  }

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

  async ensureInitialized() {
    if (!this.initialized) {
      await this.initialize();
    }
  }

  async getStats() {
    await this.ensureInitialized();

    try {
      const [memories, patterns, embeddings, syncQueue, contextCache] = await Promise.all([
        this.db.get('SELECT COUNT(*) as count FROM project_memories_cache'),
        this.db.get('SELECT COUNT(*) as count FROM workflow_patterns_cache'),
        this.db.get('SELECT COUNT(*) as count FROM embedding_cache'),
        this.db.get('SELECT COUNT(*) as count FROM sync_queue WHERE status = "pending"'),
        this.db.get('SELECT COUNT(*) as count, SUM(hit_count) as hits FROM context_cache')
      ]);

      return {
        memories: memories.count || 0,
        patterns: patterns.count || 0,
        embeddings: embeddings.count || 0,
        pendingSync: syncQueue.count || 0,
        contextCache: contextCache.count || 0,
        contextCacheHits: contextCache.hits || 0
      };
    } catch (error) {
      logger.error('Failed to get SQLite stats', { error: error.message });
      return { 
        memories: 0, 
        patterns: 0, 
        embeddings: 0, 
        pendingSync: 0,
        contextCache: 0,
        contextCacheHits: 0
      };
    }
  }

  async close() {
    if (this.db) {
      await this.db.close();
      this.initialized = false;
    }
  }
}

export default new OptimizedSQLiteClient();