import winston from 'winston';
import sqliteClient from '../core/sqlite-client.js';
import supabaseClient from '../core/supabase-client.js';
import { config } from '../../config/rag-config.js';

const logger = winston.createLogger({
  level: config.logging.level,
  format: winston.format.json(),
  transports: [
    new winston.transports.Console(),
    new winston.transports.File({ filename: config.logging.file })
  ]
});

class PatternStore {
  constructor() {
    this.cache = new Map();
    this.cacheTimeout = 300000; // 5 minutes
    this.lastCacheUpdate = 0;
  }

  /**
   * Store a new pattern
   */
  async store(pattern) {
    try {
      // Store locally first
      await sqliteClient.storePattern(pattern);

      // Store in cloud
      await supabaseClient.storePattern(pattern);

      // Update cache
      this.cache.set(pattern.id, pattern);

      logger.info('Pattern stored', {
        id: pattern.id,
        name: pattern.pattern_name
      });

      return pattern;
    } catch (error) {
      logger.error('Failed to store pattern', { error: error.message });
      throw error;
    }
  }

  /**
   * Retrieve pattern by ID
   */
  async get(patternId) {
    // Check cache first
    if (this.cache.has(patternId)) {
      return this.cache.get(patternId);
    }

    try {
      // Try local first
      const local = await this.getLocal(patternId);
      if (local) {
        this.cache.set(patternId, local);
        return local;
      }

      // Fall back to cloud
      const cloud = await this.getCloud(patternId);
      if (cloud) {
        this.cache.set(patternId, cloud);
        return cloud;
      }

      return null;
    } catch (error) {
      logger.error('Failed to retrieve pattern', { error: error.message });
      return null;
    }
  }

  /**
   * Get all patterns
   */
  async getAll(options = {}) {
    const {
      projectId = config.project.id,
      minOccurrences = 0,
      minSuccessRate = 0,
      autoApplyOnly = false
    } = options;

    try {
      await this.refreshCache();

      let patterns = Array.from(this.cache.values());

      // Apply filters
      if (projectId) {
        patterns = patterns.filter(p => 
          p.project_contexts && p.project_contexts.includes(projectId)
        );
      }

      if (minOccurrences > 0) {
        patterns = patterns.filter(p => p.occurrence_count >= minOccurrences);
      }

      if (minSuccessRate > 0) {
        patterns = patterns.filter(p => p.success_rate >= minSuccessRate);
      }

      if (autoApplyOnly) {
        patterns = patterns.filter(p => p.auto_apply === true);
      }

      return patterns;
    } catch (error) {
      logger.error('Failed to get all patterns', { error: error.message });
      return [];
    }
  }

  /**
   * Update pattern
   */
  async update(patternId, updates) {
    try {
      const pattern = await this.get(patternId);
      if (!pattern) {
        throw new Error('Pattern not found');
      }

      // Apply updates
      Object.assign(pattern, updates);
      pattern.last_used = new Date().toISOString();

      // Store updated pattern
      await this.store(pattern);

      logger.info('Pattern updated', {
        id: patternId,
        updates: Object.keys(updates)
      });

      return pattern;
    } catch (error) {
      logger.error('Failed to update pattern', { error: error.message });
      throw error;
    }
  }

  /**
   * Delete pattern
   */
  async delete(patternId) {
    try {
      // Delete from local
      await sqliteClient.run(
        'DELETE FROM workflow_patterns_cache WHERE id = ?',
        [patternId]
      );

      // Delete from cloud (would need to implement in supabase client)
      // await supabaseClient.deletePattern(patternId);

      // Remove from cache
      this.cache.delete(patternId);

      logger.info('Pattern deleted', { id: patternId });
      return true;
    } catch (error) {
      logger.error('Failed to delete pattern', { error: error.message });
      return false;
    }
  }

  /**
   * Search patterns by embedding
   */
  async search(embedding, options = {}) {
    const {
      limit = 10,
      threshold = config.rag.patternThreshold
    } = options;

    try {
      const [local, cloud] = await Promise.all([
        this.searchLocal(embedding, { limit, threshold }),
        this.searchCloud(embedding, { limit, threshold })
      ]);

      return this.mergeResults(local, cloud);
    } catch (error) {
      logger.error('Failed to search patterns', { error: error.message });
      return [];
    }
  }

  /**
   * Get local pattern
   */
  async getLocal(patternId) {
    const result = await sqliteClient.get(
      'SELECT * FROM workflow_patterns_cache WHERE id = ?',
      [patternId]
    );

    if (result) {
      return this.parsePattern(result);
    }

    return null;
  }

  /**
   * Get cloud pattern
   */
  async getCloud(patternId) {
    // Would need to implement in supabase client
    return null;
  }

  /**
   * Search local patterns
   */
  async searchLocal(embedding, options) {
    // Implementation would query SQLite
    return [];
  }

  /**
   * Search cloud patterns
   */
  async searchCloud(embedding, options) {
    return supabaseClient.searchPatterns(embedding, options);
  }

  /**
   * Merge search results
   */
  mergeResults(local, cloud) {
    const seen = new Set();
    const merged = [];

    for (const pattern of [...cloud, ...local]) {
      if (!seen.has(pattern.id)) {
        seen.add(pattern.id);
        merged.push(pattern);
      }
    }

    return merged.sort((a, b) => b.similarity - a.similarity);
  }

  /**
   * Parse pattern from database row
   */
  parsePattern(row) {
    return {
      id: row.id,
      pattern_hash: row.pattern_hash,
      pattern_name: row.pattern_name,
      trigger_embedding: JSON.parse(row.trigger_embedding_json || '[]'),
      action_sequence: JSON.parse(row.action_sequence || '{}'),
      occurrence_count: row.occurrence_count,
      success_rate: row.success_rate,
      last_used: new Date(row.last_used * 1000).toISOString(),
      project_contexts: JSON.parse(row.project_contexts || '[]'),
      auto_apply: row.auto_apply === 1
    };
  }

  /**
   * Refresh cache from database
   */
  async refreshCache() {
    const now = Date.now();
    
    if (now - this.lastCacheUpdate < this.cacheTimeout) {
      return;
    }

    try {
      const patterns = await sqliteClient.all(
        'SELECT * FROM workflow_patterns_cache ORDER BY occurrence_count DESC LIMIT 100'
      );

      this.cache.clear();
      
      for (const row of patterns) {
        const pattern = this.parsePattern(row);
        this.cache.set(pattern.id, pattern);
      }

      this.lastCacheUpdate = now;
      logger.debug('Pattern cache refreshed', { count: this.cache.size });
    } catch (error) {
      logger.error('Failed to refresh pattern cache', { error: error.message });
    }
  }

  /**
   * Get pattern statistics
   */
  async getStats() {
    try {
      const stats = await sqliteClient.get(`
        SELECT 
          COUNT(*) as total,
          COUNT(CASE WHEN auto_apply = 1 THEN 1 END) as auto_apply,
          AVG(occurrence_count) as avg_occurrences,
          AVG(success_rate) as avg_success_rate
        FROM workflow_patterns_cache
      `);

      return {
        totalPatterns: stats.total || 0,
        autoApplyPatterns: stats.auto_apply || 0,
        averageOccurrences: stats.avg_occurrences || 0,
        averageSuccessRate: stats.avg_success_rate || 0,
        cacheSize: this.cache.size
      };
    } catch (error) {
      logger.error('Failed to get pattern stats', { error: error.message });
      return {
        totalPatterns: 0,
        autoApplyPatterns: 0,
        averageOccurrences: 0,
        averageSuccessRate: 0,
        cacheSize: 0
      };
    }
  }

  /**
   * Export patterns for backup
   */
  async export() {
    try {
      const patterns = await this.getAll();
      
      return {
        version: '1.0',
        timestamp: new Date().toISOString(),
        patterns: patterns.map(p => ({
          ...p,
          trigger_embedding: undefined // Remove embeddings for smaller export
        }))
      };
    } catch (error) {
      logger.error('Failed to export patterns', { error: error.message });
      throw error;
    }
  }

  /**
   * Import patterns from backup
   */
  async import(data) {
    try {
      if (!data.patterns || !Array.isArray(data.patterns)) {
        throw new Error('Invalid import data');
      }

      let imported = 0;
      
      for (const pattern of data.patterns) {
        // Regenerate embeddings if needed
        if (!pattern.trigger_embedding && pattern.action_sequence.template) {
          const embedding = await embeddingService.generateEmbedding(
            pattern.action_sequence.template.trigger
          );
          pattern.trigger_embedding = embedding;
        }

        await this.store(pattern);
        imported++;
      }

      logger.info('Patterns imported', { count: imported });
      return imported;
    } catch (error) {
      logger.error('Failed to import patterns', { error: error.message });
      throw error;
    }
  }
}

export default new PatternStore();