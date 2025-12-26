import winston from 'winston';
import memoryStore from './memory-store.js';
import embeddingService from '../core/embedding-service.js';
import { config } from '../../config/rag-config.js';

const logger = winston.createLogger({
  level: config.logging.level,
  format: winston.format.json(),
  transports: [
    new winston.transports.Console(),
    new winston.transports.File({ filename: config.logging.file })
  ]
});

class ContextRetriever {
  constructor() {
    this.cache = new Map();
    this.cacheTimeout = 60000; // 1 minute cache
  }

  /**
   * Retrieve context for a query with dynamic sizing
   */
  async retrieveContext(query, options = {}) {
    const {
      maxItems = config.rag.maxContextItems,
      minSimilarity = config.rag.similarityThreshold,
      includeMetadata = true,
      contextType = 'all' // all, code, documentation, conversation
    } = options;

    const startTime = Date.now();

    try {
      // Check cache
      const cacheKey = this.getCacheKey(query, options);
      const cached = this.getFromCache(cacheKey);
      if (cached) {
        logger.debug('Context cache hit', { cacheKey });
        return cached;
      }

      // Retrieve base memories
      const memories = await memoryStore.retrieve(query, {
        limit: maxItems * 2, // Get more for filtering
        ...options
      });

      // Filter by context type if specified
      const filtered = this.filterByType(memories, contextType);

      // Calculate dynamic context size based on token limits
      const sized = await this.dynamicSizing(filtered, maxItems);

      // Format context for use
      const context = this.formatContext(sized, includeMetadata);

      // Cache result
      this.setCache(cacheKey, context);

      const elapsed = Date.now() - startTime;
      logger.info('Context retrieved', {
        query: query.substring(0, 50),
        items: context.items.length,
        elapsed
      });

      return context;
    } catch (error) {
      logger.error('Failed to retrieve context', { error: error.message });
      return { items: [], metadata: {} };
    }
  }

  /**
   * Retrieve context with pattern matching
   */
  async retrieveWithPatterns(query, options = {}) {
    try {
      // Get base context
      const context = await this.retrieveContext(query, options);

      // Check for matching patterns
      const patterns = await this.findMatchingPatterns(query);

      if (patterns.length > 0) {
        context.patterns = patterns;
        context.suggestedActions = this.extractSuggestedActions(patterns);
      }

      return context;
    } catch (error) {
      logger.error('Failed to retrieve context with patterns', { error: error.message });
      return { items: [], metadata: {} };
    }
  }

  /**
   * Filter memories by type
   */
  filterByType(memories, type) {
    if (type === 'all') return memories;

    const typeFilters = {
      code: (m) => m.interaction_type === 'code' || m.file_paths?.some(p => /\.(js|ts|py|java|go)$/.test(p)),
      documentation: (m) => m.interaction_type === 'documentation' || m.file_paths?.some(p => /\.(md|txt|doc)$/.test(p)),
      conversation: (m) => m.interaction_type === 'conversation' || !m.file_paths?.length
    };

    const filter = typeFilters[type];
    return filter ? memories.filter(filter) : memories;
  }

  /**
   * Dynamic sizing based on token estimates
   */
  async dynamicSizing(memories, maxItems) {
    const maxTokens = 8000; // Conservative estimate for context window
    let totalTokens = 0;
    const selected = [];

    for (const memory of memories) {
      // Rough token estimate (4 chars per token)
      const estimatedTokens = Math.ceil(memory.content.length / 4);
      
      if (totalTokens + estimatedTokens > maxTokens) {
        break;
      }

      if (selected.length >= maxItems) {
        break;
      }

      selected.push(memory);
      totalTokens += estimatedTokens;
    }

    return selected;
  }

  /**
   * Format context for consumption
   */
  formatContext(memories, includeMetadata) {
    const items = memories.map(memory => {
      const item = {
        id: memory.id,
        content: memory.content,
        similarity: memory.score || memory.similarity,
        type: memory.interaction_type
      };

      if (includeMetadata) {
        item.metadata = memory.metadata;
        item.filePaths = memory.file_paths;
        item.toolChain = memory.tool_chain;
        item.timestamp = memory.created_at;
      }

      return item;
    });

    const metadata = {
      totalItems: items.length,
      averageSimilarity: items.reduce((sum, item) => sum + item.similarity, 0) / items.length || 0,
      types: [...new Set(items.map(i => i.type))],
      timestamp: new Date().toISOString()
    };

    return { items, metadata };
  }

  /**
   * Find matching workflow patterns
   */
  async findMatchingPatterns(query) {
    try {
      const embedding = await embeddingService.generateEmbedding(query);
      
      // Search for patterns in both local and cloud storage
      const patterns = await Promise.all([
        this.searchLocalPatterns(embedding),
        this.searchCloudPatterns(embedding)
      ]);

      return this.mergePatterns(patterns[0], patterns[1]);
    } catch (error) {
      logger.error('Failed to find matching patterns', { error: error.message });
      return [];
    }
  }

  /**
   * Search local patterns
   */
  async searchLocalPatterns(embedding) {
    // Implementation would query SQLite for patterns
    return [];
  }

  /**
   * Search cloud patterns
   */
  async searchCloudPatterns(embedding) {
    // Implementation would query Supabase for patterns
    return [];
  }

  /**
   * Merge pattern results
   */
  mergePatterns(local, cloud) {
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
   * Extract suggested actions from patterns
   */
  extractSuggestedActions(patterns) {
    const actions = [];

    for (const pattern of patterns) {
      if (pattern.auto_apply && pattern.success_rate > 0.8) {
        actions.push({
          patternId: pattern.id,
          name: pattern.pattern_name,
          confidence: pattern.similarity * pattern.success_rate,
          actions: pattern.action_sequence
        });
      }
    }

    return actions.sort((a, b) => b.confidence - a.confidence);
  }

  /**
   * Generate cache key
   */
  getCacheKey(query, options) {
    const key = JSON.stringify({ query, ...options });
    return require('crypto').createHash('md5').update(key).digest('hex');
  }

  /**
   * Get from cache
   */
  getFromCache(key) {
    const cached = this.cache.get(key);
    if (cached && Date.now() - cached.timestamp < this.cacheTimeout) {
      return cached.data;
    }
    this.cache.delete(key);
    return null;
  }

  /**
   * Set cache
   */
  setCache(key, data) {
    this.cache.set(key, {
      data,
      timestamp: Date.now()
    });

    // Clean old cache entries
    if (this.cache.size > 100) {
      const entries = Array.from(this.cache.entries());
      entries.sort((a, b) => a[1].timestamp - b[1].timestamp);
      
      for (let i = 0; i < 50; i++) {
        this.cache.delete(entries[i][0]);
      }
    }
  }

  /**
   * Clear cache
   */
  clearCache() {
    this.cache.clear();
    logger.info('Context cache cleared');
  }
}

export default new ContextRetriever();