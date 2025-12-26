import { v4 as uuidv4 } from 'uuid';
import winston from 'winston';
import embeddingService from '../core/embedding-service.js';
import supabaseClient from '../core/supabase-client.js';
import sqliteClient from '../core/sqlite-client.js';
import { config } from '../../config/rag-config.js';

const logger = winston.createLogger({
  level: config.logging.level,
  format: winston.format.json(),
  transports: [
    new winston.transports.Console(),
    new winston.transports.File({ filename: config.logging.file })
  ]
});

class MemoryStore {
  constructor() {
    this.sessionId = uuidv4();
    this.syncInterval = null;
    this.initialized = false;
  }

  /**
   * Initialize memory store
   */
  async initialize() {
    if (this.initialized) return;

    try {
      // Initialize storage clients
      await Promise.all([
        sqliteClient.initialize(),
        supabaseClient.initialize()
      ]);

      // Start sync process
      this.startSync();

      this.initialized = true;
      logger.info('Memory store initialized successfully');
    } catch (error) {
      logger.error('Failed to initialize memory store', { error: error.message });
      throw error;
    }
  }

  /**
   * Store a new memory
   */
  async store(content, options = {}) {
    await this.ensureInitialized();

    const {
      interactionType = 'general',
      toolChain = [],
      filePaths = [],
      successScore = 1.0,
      metadata = {}
    } = options;

    try {
      // Generate embedding for the content
      const embedding = await embeddingService.generateEmbedding(content);

      // Create memory object
      const memory = {
        id: uuidv4(),
        project_id: config.project.id,
        content,
        embedding,
        metadata: {
          ...metadata,
          timestamp: new Date().toISOString(),
          sessionId: this.sessionId
        },
        interaction_type: interactionType,
        tool_chain: toolChain,
        file_paths: filePaths,
        success_score: successScore,
        created_at: new Date().toISOString(),
        session_id: this.sessionId,
        user_id: config.project.userId
      };

      // Store locally first (immediate)
      await sqliteClient.storeMemory(memory);

      // Queue for cloud storage (async)
      this.queueCloudSync(memory);

      logger.info('Memory stored successfully', { 
        id: memory.id,
        type: interactionType 
      });

      return memory;
    } catch (error) {
      logger.error('Failed to store memory', { error: error.message });
      throw error;
    }
  }

  /**
   * Store multiple memories in batch
   */
  async storeBatch(memories) {
    await this.ensureInitialized();

    const results = [];

    try {
      // Generate embeddings for all memories
      const contents = memories.map(m => m.content);
      const embeddings = await embeddingService.generateEmbeddings(contents);

      // Process each memory
      for (let i = 0; i < memories.length; i++) {
        const memory = {
          id: uuidv4(),
          project_id: config.project.id,
          content: memories[i].content,
          embedding: embeddings[i],
          metadata: {
            ...memories[i].metadata,
            timestamp: new Date().toISOString(),
            sessionId: this.sessionId
          },
          interaction_type: memories[i].interactionType || 'general',
          tool_chain: memories[i].toolChain || [],
          file_paths: memories[i].filePaths || [],
          success_score: memories[i].successScore || 1.0,
          created_at: new Date().toISOString(),
          session_id: this.sessionId,
          user_id: config.project.userId
        };

        // Store locally
        await sqliteClient.storeMemory(memory);
        results.push(memory);
      }

      // Queue batch for cloud sync
      this.queueCloudSyncBatch(results);

      logger.info('Batch memories stored successfully', { count: results.length });
      return results;
    } catch (error) {
      logger.error('Failed to store batch memories', { error: error.message });
      throw error;
    }
  }

  /**
   * Retrieve relevant memories
   */
  async retrieve(query, options = {}) {
    await this.ensureInitialized();

    const {
      limit = config.rag.maxContextItems,
      includePatterns = true,
      includeKnowledge = true,
      boostCurrentProject = true,
      boostRecent = true
    } = options;

    try {
      // Generate embedding for query
      const queryEmbedding = await embeddingService.generateEmbedding(query);

      // Search in parallel from both sources
      const [localResults, cloudResults] = await Promise.all([
        this.searchLocal(queryEmbedding, { limit: limit * 2 }),
        this.searchCloud(queryEmbedding, { limit: limit * 2 })
      ]);

      // Merge and deduplicate results
      const merged = this.mergeResults(localResults, cloudResults);

      // Apply boosting
      const boosted = this.applyBoosts(merged, {
        boostCurrentProject,
        boostRecent
      });

      // Sort by final score and limit
      const sorted = boosted
        .sort((a, b) => b.score - a.score)
        .slice(0, limit);

      logger.info('Memories retrieved', { 
        query: query.substring(0, 50),
        count: sorted.length 
      });

      return sorted;
    } catch (error) {
      logger.error('Failed to retrieve memories', { error: error.message });
      return [];
    }
  }

  /**
   * Search local cache
   */
  async searchLocal(embedding, options = {}) {
    try {
      const results = await sqliteClient.searchMemories(embedding, options);
      return results.map(r => ({
        ...r,
        source: 'local',
        score: r.similarity
      }));
    } catch (error) {
      logger.warn('Local search failed', { error: error.message });
      return [];
    }
  }

  /**
   * Search cloud storage
   */
  async searchCloud(embedding, options = {}) {
    try {
      // Set a timeout for cloud search
      const timeoutPromise = new Promise((resolve) => 
        setTimeout(() => resolve([]), config.rag.retrievalTimeoutMs)
      );

      const searchPromise = supabaseClient.searchMemories(embedding, options);
      
      const results = await Promise.race([searchPromise, timeoutPromise]);
      
      return results.map(r => ({
        ...r,
        source: 'cloud',
        score: r.similarity
      }));
    } catch (error) {
      logger.warn('Cloud search failed', { error: error.message });
      return [];
    }
  }

  /**
   * Merge and deduplicate results
   */
  mergeResults(local, cloud) {
    const seen = new Set();
    const merged = [];

    // Add all results, preferring cloud version if duplicate
    for (const result of [...cloud, ...local]) {
      if (!seen.has(result.id)) {
        seen.add(result.id);
        merged.push(result);
      }
    }

    return merged;
  }

  /**
   * Apply score boosts
   */
  applyBoosts(results, options = {}) {
    const now = Date.now();
    const recentThreshold = 3600000; // 1 hour

    return results.map(result => {
      let score = result.score;

      // Boost current project
      if (options.boostCurrentProject && result.project_id === config.project.id) {
        score *= config.rag.contextBoostCurrentProject;
      }

      // Boost recent items
      if (options.boostRecent) {
        const age = now - new Date(result.created_at).getTime();
        if (age < recentThreshold) {
          score *= config.rag.contextBoostRecent;
        }
      }

      // Boost by success score
      if (result.success_score) {
        score *= (0.8 + 0.2 * result.success_score);
      }

      return { ...result, score };
    });
  }

  /**
   * Queue memory for cloud sync
   */
  queueCloudSync(memory) {
    // Add to SQLite sync queue (handled by sync process)
    sqliteClient.addToSyncQueue('project_memories', memory.id, 'INSERT', memory);
  }

  /**
   * Queue batch for cloud sync
   */
  queueCloudSyncBatch(memories) {
    for (const memory of memories) {
      this.queueCloudSync(memory);
    }
  }

  /**
   * Start sync process
   */
  startSync() {
    this.syncInterval = setInterval(async () => {
      await this.syncToCloud();
    }, config.database.syncIntervalMs);
  }

  /**
   * Sync local data to cloud
   */
  async syncToCloud() {
    try {
      const items = await sqliteClient.getSyncQueue(config.database.syncBatchSize);
      
      if (items.length === 0) return;

      const memoriesMap = new Map();

      // Deduplicate by ID, keeping the latest version
      items
        .filter(item => item.table_name === 'project_memories')
        .forEach(item => {
          const payload = JSON.parse(item.payload);
          // Remove fields that don't exist in Supabase schema
          const { file_paths, tool_chain, interaction_type, session_id, user_id, success_score, ...cleanPayload } = payload;
          memoriesMap.set(cleanPayload.id, cleanPayload);
        });

      const memories = Array.from(memoriesMap.values());

      if (memories.length > 0) {
        await supabaseClient.storeMemories(memories);
        
        // Mark as synced
        for (const item of items) {
          await sqliteClient.markSyncCompleted(item.id);
        }

        logger.info('Synced memories to cloud', { count: memories.length });
      }
    } catch (error) {
      logger.error('Failed to sync to cloud', { error: error.message });
    }
  }

  /**
   * Update memory success score
   */
  async updateSuccessScore(memoryId, score) {
    try {
      // Update locally
      await sqliteClient.run(
        'UPDATE project_memories_cache SET success_score = ? WHERE id = ?',
        [score, memoryId]
      );

      // Queue update for cloud
      sqliteClient.addToSyncQueue('project_memories', memoryId, 'UPDATE', {
        id: memoryId,
        success_score: score
      });

      logger.debug('Updated memory success score', { id: memoryId, score });
    } catch (error) {
      logger.error('Failed to update success score', { error: error.message });
    }
  }

  /**
   * Get memory statistics
   */
  async getStats() {
    await this.ensureInitialized();

    const [localStats, cloudStats] = await Promise.all([
      sqliteClient.getStats(),
      supabaseClient.getStats()
    ]);

    return {
      local: localStats,
      cloud: cloudStats,
      sessionId: this.sessionId
    };
  }

  /**
   * Clear local cache
   */
  async clearLocalCache() {
    await sqliteClient.run('DELETE FROM project_memories_cache WHERE synced_to_cloud = 1');
    logger.info('Local cache cleared');
  }

  /**
   * Ensure store is initialized
   */
  async ensureInitialized() {
    if (!this.initialized) {
      await this.initialize();
    }
  }

  /**
   * Stop sync process
   */
  stopSync() {
    if (this.syncInterval) {
      clearInterval(this.syncInterval);
      this.syncInterval = null;
    }
  }
}

export default new MemoryStore();