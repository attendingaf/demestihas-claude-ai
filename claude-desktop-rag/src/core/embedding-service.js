import OpenAI from 'openai';
import { LRUCache } from 'lru-cache';
import crypto from 'crypto';
import PQueue from 'p-queue';
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

class EmbeddingService {
  constructor() {
    this.openai = new OpenAI({
      apiKey: config.openai.apiKey
    });

    // LRU cache for embeddings (1 hour TTL)
    this.cache = new LRUCache({
      max: config.performance.maxEmbeddingCacheSize,
      ttl: config.openai.cacheTTL * 1000
    });

    // Queue for batch processing
    this.queue = new PQueue({ 
      concurrency: config.performance.maxConcurrentEmbeddings 
    });

    this.batchQueue = [];
    this.batchTimer = null;
    this.batchPromises = new Map();
  }

  /**
   * Generate embedding for a single text
   */
  async generateEmbedding(text, options = {}) {
    if (!text || text.trim().length === 0) {
      throw new Error('Text cannot be empty');
    }

    // Check cache first
    const cacheKey = this.getCacheKey(text);
    const cached = this.cache.get(cacheKey);
    if (cached && !options.skipCache) {
      logger.debug('Embedding cache hit', { cacheKey });
      return cached;
    }

    // Add to batch queue
    if (options.batch !== false) {
      return this.addToBatch(text, cacheKey);
    }

    // Generate immediately
    return this.generateSingle(text, cacheKey);
  }

  /**
   * Generate embeddings for multiple texts
   */
  async generateEmbeddings(texts, options = {}) {
    const uniqueTexts = [...new Set(texts.filter(t => t && t.trim().length > 0))];
    
    if (uniqueTexts.length === 0) {
      return [];
    }

    // Check cache for all texts
    const results = new Map();
    const uncachedTexts = [];

    for (const text of uniqueTexts) {
      const cacheKey = this.getCacheKey(text);
      const cached = this.cache.get(cacheKey);
      
      if (cached && !options.skipCache) {
        results.set(text, cached);
      } else {
        uncachedTexts.push(text);
      }
    }

    // Process uncached texts in batches
    if (uncachedTexts.length > 0) {
      const batches = this.createBatches(uncachedTexts, config.openai.batchSize);
      
      const batchResults = await Promise.all(
        batches.map(batch => this.queue.add(() => this.processBatch(batch)))
      );

      for (const batchResult of batchResults) {
        for (const [text, embedding] of batchResult) {
          results.set(text, embedding);
        }
      }
    }

    // Return in original order
    return texts.map(text => results.get(text));
  }

  /**
   * Process a batch of texts
   */
  async processBatch(texts) {
    const maxRetries = config.performance.retryAttempts;
    let lastError;

    for (let attempt = 0; attempt < maxRetries; attempt++) {
      try {
        const response = await this.openai.embeddings.create({
          model: config.openai.embeddingModel,
          input: texts,
          dimensions: config.openai.embeddingDimensions
        });

        const results = new Map();
        
        for (let i = 0; i < texts.length; i++) {
          const embedding = response.data[i].embedding;
          const text = texts[i];
          const cacheKey = this.getCacheKey(text);
          
          // Cache the result
          this.cache.set(cacheKey, embedding);
          results.set(text, embedding);
        }

        logger.info('Batch embeddings generated', { 
          count: texts.length,
          attempt: attempt + 1 
        });

        return results;
      } catch (error) {
        lastError = error;
        logger.warn('Embedding batch failed, retrying...', { 
          attempt: attempt + 1,
          error: error.message 
        });
        
        if (attempt < maxRetries - 1) {
          await this.delay(config.performance.retryDelayMs * Math.pow(2, attempt));
        }
      }
    }

    throw lastError;
  }

  /**
   * Generate embedding for single text
   */
  async generateSingle(text, cacheKey) {
    const maxRetries = config.performance.retryAttempts;
    let lastError;

    for (let attempt = 0; attempt < maxRetries; attempt++) {
      try {
        const response = await this.openai.embeddings.create({
          model: config.openai.embeddingModel,
          input: text,
          dimensions: config.openai.embeddingDimensions
        });

        const embedding = response.data[0].embedding;
        
        // Cache the result
        this.cache.set(cacheKey, embedding);
        
        logger.debug('Single embedding generated', { cacheKey });
        return embedding;
      } catch (error) {
        lastError = error;
        logger.warn('Single embedding failed, retrying...', { 
          attempt: attempt + 1,
          error: error.message 
        });
        
        if (attempt < maxRetries - 1) {
          await this.delay(config.performance.retryDelayMs * Math.pow(2, attempt));
        }
      }
    }

    throw lastError;
  }

  /**
   * Add text to batch queue
   */
  addToBatch(text, cacheKey) {
    return new Promise((resolve, reject) => {
      this.batchQueue.push({ text, cacheKey, resolve, reject });
      
      // Clear existing timer
      if (this.batchTimer) {
        clearTimeout(this.batchTimer);
      }
      
      // Process batch when full or after delay
      if (this.batchQueue.length >= config.openai.batchSize) {
        this.processBatchQueue();
      } else {
        this.batchTimer = setTimeout(() => this.processBatchQueue(), 100);
      }
    });
  }

  /**
   * Process queued batch items
   */
  async processBatchQueue() {
    if (this.batchQueue.length === 0) return;

    const items = this.batchQueue.splice(0, config.openai.batchSize);
    const texts = items.map(item => item.text);

    try {
      const results = await this.processBatch(texts);
      
      for (const item of items) {
        const embedding = results.get(item.text);
        if (embedding) {
          item.resolve(embedding);
        } else {
          item.reject(new Error('Embedding not found in batch results'));
        }
      }
    } catch (error) {
      for (const item of items) {
        item.reject(error);
      }
    }
  }

  /**
   * Calculate cosine similarity between two embeddings
   */
  cosineSimilarity(embedding1, embedding2) {
    if (!embedding1 || !embedding2) return 0;
    if (embedding1.length !== embedding2.length) {
      throw new Error('Embeddings must have the same dimensions');
    }

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
   * Find most similar embeddings
   */
  findSimilar(targetEmbedding, embeddings, threshold = config.rag.similarityThreshold) {
    const similarities = embeddings.map((item, index) => ({
      ...item,
      index,
      similarity: this.cosineSimilarity(targetEmbedding, item.embedding)
    }));

    return similarities
      .filter(item => item.similarity >= threshold)
      .sort((a, b) => b.similarity - a.similarity);
  }

  /**
   * Generate cache key for text
   */
  getCacheKey(text) {
    return crypto.createHash('sha256')
      .update(text + config.openai.embeddingModel)
      .digest('hex');
  }

  /**
   * Create batches from array
   */
  createBatches(array, batchSize) {
    const batches = [];
    for (let i = 0; i < array.length; i += batchSize) {
      batches.push(array.slice(i, i + batchSize));
    }
    return batches;
  }

  /**
   * Delay helper
   */
  delay(ms) {
    return new Promise(resolve => setTimeout(resolve, ms));
  }

  /**
   * Clear cache
   */
  clearCache() {
    this.cache.clear();
    logger.info('Embedding cache cleared');
  }

  /**
   * Get cache statistics
   */
  getCacheStats() {
    return {
      size: this.cache.size,
      calculatedSize: this.cache.calculatedSize,
      hits: this.cache.hits,
      misses: this.cache.misses
    };
  }
}

export default new EmbeddingService();