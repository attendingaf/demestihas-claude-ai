import { v4 as uuidv4 } from 'uuid';
import winston from 'winston';
import embeddingService from '../core/embedding-service.js';
import supabaseClient from '../core/supabase-client.js';
import sqliteClientOptimized from '../core/sqlite-client-optimized.js';
import sqliteMigration from '../core/sqlite-migration.js';
import projectContextManager from '../context/project-context-manager.js';
import contextPrioritizer from '../context/context-prioritizer.js';
import syncEngine from '../sync/sync-engine.js';
import performanceMonitor from '../monitoring/performance-monitor.js';
import { config } from '../../config/rag-config.js';

const logger = winston.createLogger({
  level: config.logging.level,
  format: winston.format.json(),
  transports: [
    new winston.transports.Console(),
    new winston.transports.File({ filename: config.logging.file })
  ]
});

class MemoryStoreV2 {
  constructor() {
    this.sessionId = uuidv4();
    this.initialized = false;
    this.sqliteClient = sqliteClientOptimized; // Use optimized client
    this.useOptimizations = true;
  }

  async initialize() {
    if (this.initialized) return;

    try {
      // Run migration if needed
      await sqliteMigration.migrate();
      
      // Initialize all components
      await Promise.all([
        this.sqliteClient.initialize(),
        supabaseClient.initialize(),
        projectContextManager.initialize(),
        contextPrioritizer.initialize(),
        syncEngine.initialize(),
        performanceMonitor.initialize()
      ]);

      this.initialized = true;
      logger.info('Memory Store V2 initialized with optimizations');
    } catch (error) {
      logger.error('Failed to initialize Memory Store V2', { error: error.message });
      throw error;
    }
  }

  async storeMemory(content, metadata = {}) {
    await this.ensureInitialized();
    const startTime = Date.now();

    try {
      // Generate embedding
      const embedding = await embeddingService.generateEmbedding(content);

      // Create memory object
      const memory = {
        id: uuidv4(),
        project_id: metadata.project_id || config.project.id,
        content,
        embedding,
        metadata: {
          ...metadata,
          timestamp: new Date().toISOString(),
          session_id: this.sessionId,
          user_id: config.user.id
        },
        interaction_type: metadata.interaction_type || 'manual',
        tool_chain: metadata.tool_chain || [],
        file_paths: metadata.file_paths || [],
        success_score: metadata.success_score || 1.0,
        session_id: this.sessionId,
        user_id: config.user.id
      };

      // Store locally with optimized client
      await this.sqliteClient.storeMemory(memory);

      // Track performance
      performanceMonitor.trackRetrievalTime(Date.now() - startTime, 'store');

      // Update recent interactions for prioritization
      await contextPrioritizer.updateRecentInteractions(memory);

      logger.debug('Memory stored with optimizations', { 
        id: memory.id,
        time: Date.now() - startTime 
      });

      return memory;
    } catch (error) {
      logger.error('Failed to store memory', { error: error.message });
      throw error;
    }
  }

  async searchMemories(query, options = {}) {
    await this.ensureInitialized();
    const startTime = Date.now();

    try {
      // Generate query embedding
      const embedding = await embeddingService.generateEmbedding(query);

      // Use context-aware search if optimizations are enabled
      let results;
      
      if (this.useOptimizations) {
        // Search with project context
        results = await projectContextManager.searchWithContext(embedding, options);
        
        // Apply priority boosting
        results = await contextPrioritizer.prioritizeResults(results, query, options);
      } else {
        // Fallback to basic search
        results = await this.sqliteClient.searchMemories(embedding, options);
      }

      // Track performance
      const searchTime = Date.now() - startTime;
      performanceMonitor.trackRetrievalTime(searchTime, 'search');

      // Check context isolation
      if (options.projectId) {
        performanceMonitor.checkContextIsolation(options.projectId, results);
      }

      logger.debug('Memories searched with optimizations', {
        count: results.length,
        time: searchTime,
        cacheHit: searchTime < 50 // Likely cache hit if very fast
      });

      return results;
    } catch (error) {
      logger.error('Failed to search memories', { error: error.message });
      return [];
    }
  }

  async switchProject(projectId) {
    await this.ensureInitialized();
    
    try {
      const context = await projectContextManager.switchProject(projectId);
      
      logger.info('Project switched', { 
        projectId,
        memoriesLoaded: context.memories.length,
        patternsLoaded: context.patterns.length
      });
      
      return context;
    } catch (error) {
      logger.error('Failed to switch project', { error: error.message });
      throw error;
    }
  }

  async setCurrentContext(file, functionName = null) {
    contextPrioritizer.setCurrentContext(file, functionName);
  }

  async getPerformanceMetrics() {
    await this.ensureInitialized();
    
    const metrics = await performanceMonitor.getMetrics();
    const detailed = await performanceMonitor.getDetailedReport();
    
    return {
      summary: {
        avgRetrievalTime: metrics.retrieval.avg,
        cacheHitRate: metrics.cache.hitRate,
        syncLatency: metrics.sync.avgLatency,
        contextSwitchTime: metrics.context.avgSwitchTime,
        health: metrics.health
      },
      detailed
    };
  }

  async optimizePerformance() {
    logger.info('Running performance optimization...');
    
    try {
      // Precompute frequent queries
      await this.sqliteClient.precomputeFrequentQueries();
      
      // Clean up old contexts
      await projectContextManager.cleanup();
      
      // Prune old data
      await this.sqliteClient.pruneOldData();
      
      // Force sync
      await syncEngine.syncAll();
      
      logger.info('Performance optimization completed');
    } catch (error) {
      logger.error('Performance optimization failed', { error: error.message });
    }
  }

  async getStats() {
    await this.ensureInitialized();
    
    const sqliteStats = await this.sqliteClient.getStats();
    const syncStats = await syncEngine.getMetrics();
    const contextStats = await projectContextManager.getMetrics();
    const perfStats = await performanceMonitor.getMetrics();
    
    return {
      storage: sqliteStats,
      sync: {
        isOnline: syncStats.isOnline,
        pendingSync: syncStats.pendingSyncItems,
        lastSync: syncStats.lastSyncTime
      },
      context: {
        currentProject: contextStats.currentProject,
        loadedContexts: contextStats.loadedContexts
      },
      performance: {
        health: perfStats.health,
        avgRetrievalTime: perfStats.retrieval.avg,
        cacheHitRate: perfStats.cache.hitRate
      }
    };
  }

  async ensureInitialized() {
    if (!this.initialized) {
      await this.initialize();
    }
  }

  toggleOptimizations(enabled) {
    this.useOptimizations = enabled;
    logger.info(`Optimizations ${enabled ? 'enabled' : 'disabled'}`);
  }

  async close() {
    if (this.initialized) {
      await syncEngine.stop();
      performanceMonitor.stop();
      await this.sqliteClient.close();
      this.initialized = false;
      logger.info('Memory Store V2 closed');
    }
  }
}

export default new MemoryStoreV2();