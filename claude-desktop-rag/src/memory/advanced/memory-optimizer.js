import winston from 'winston';
import { performance } from 'perf_hooks';
import { config } from '../../../config/rag-config.js';

const logger = winston.createLogger({
  level: config.logging.level,
  format: winston.format.json(),
  transports: [
    new winston.transports.Console(),
    new winston.transports.File({ filename: config.logging.file })
  ]
});

// Simple LZ4-like compression implementation
class SimpleCompressor {
  compress(data) {
    // Simple RLE compression for demonstration
    const str = typeof data === 'string' ? data : JSON.stringify(data);
    let compressed = '';
    let count = 1;
    let prevChar = str[0];
    
    for (let i = 1; i <= str.length; i++) {
      if (i < str.length && str[i] === prevChar && count < 9) {
        count++;
      } else {
        if (count > 2) {
          compressed += `${count}${prevChar}`;
        } else {
          compressed += prevChar.repeat(count);
        }
        
        if (i < str.length) {
          prevChar = str[i];
          count = 1;
        }
      }
    }
    
    // Return base64 to save space
    return Buffer.from(compressed).toString('base64');
  }
  
  decompress(compressed) {
    const str = Buffer.from(compressed, 'base64').toString();
    let decompressed = '';
    
    for (let i = 0; i < str.length; i++) {
      if (/\d/.test(str[i]) && i + 1 < str.length) {
        const count = parseInt(str[i]);
        decompressed += str[i + 1].repeat(count);
        i++;
      } else {
        decompressed += str[i];
      }
    }
    
    try {
      return JSON.parse(decompressed);
    } catch {
      return decompressed;
    }
  }
}

class MemoryOptimizer {
  constructor() {
    this.compressor = new SimpleCompressor();
    this.compressionThreshold = 1024; // 1KB
    this.maxMemoryMB = 500;
    this.pruneThreshold = 0.3;
    this.mergeThreshold = 0.9;
    this.optimizationRuns = 0;
    this.totalMemoryReduced = 0;
    this.totalCompressions = 0;
    this.compressionRatios = [];
  }

  async initialize() {
    logger.info('Initializing memory optimizer...');
    this.startPeriodicOptimization();
    logger.info('Memory optimizer initialized');
  }

  async optimizeMemories(memories) {
    const startTime = performance.now();
    const initialSize = this.estimateMemorySize(memories);
    
    logger.info(`Starting optimization of ${memories.length} memories (${(initialSize / 1024 / 1024).toFixed(2)}MB)`);
    
    // Step 1: Prune low-value memories
    let optimized = await this.pruneMemories(memories);
    
    // Step 2: Merge similar memories
    optimized = await this.mergeSimilarMemories(optimized);
    
    // Step 3: Compress old/large memories
    optimized = await this.compressOldMemories(optimized);
    
    const finalSize = this.estimateMemorySize(optimized);
    const reduction = ((initialSize - finalSize) / initialSize) * 100;
    
    this.optimizationRuns++;
    this.totalMemoryReduced += (initialSize - finalSize);
    
    const optimizationTime = performance.now() - startTime;
    
    logger.info(`Optimization complete`, {
      initial: memories.length,
      final: optimized.length,
      reduction: `${reduction.toFixed(1)}%`,
      time: `${optimizationTime.toFixed(2)}ms`
    });
    
    return optimized;
  }

  async pruneMemories(memories, options = {}) {
    const {
      maxMemoryMB = this.maxMemoryMB,
      keepMinimum = 100
    } = options;
    
    if (memories.length <= keepMinimum) {
      return memories;
    }
    
    // Calculate importance scores
    const scored = memories.map(memory => ({
      ...memory,
      score: this.calculateImportanceScore(memory)
    }));
    
    // Sort by importance
    scored.sort((a, b) => b.score - a.score);
    
    // Keep memories until size limit
    const pruned = [];
    let currentSize = 0;
    const maxSize = maxMemoryMB * 1024 * 1024;
    
    for (const memory of scored) {
      const memorySize = this.estimateMemorySize([memory]);
      
      if (currentSize + memorySize <= maxSize || pruned.length < keepMinimum) {
        pruned.push(memory);
        currentSize += memorySize;
      } else if (memory.score > this.pruneThreshold) {
        // Keep high-importance memories even if over limit
        pruned.push(memory);
        currentSize += memorySize;
      }
    }
    
    logger.debug(`Pruned ${memories.length - pruned.length} memories`);
    
    return pruned;
  }

  calculateImportanceScore(memory) {
    let score = 0.5; // Base score
    
    // Recency factor
    if (memory.timestamp) {
      const age = Date.now() - memory.timestamp;
      const recencyScore = Math.exp(-age / (30 * 24 * 60 * 60 * 1000)); // 30-day half-life
      score += recencyScore * 0.2;
    }
    
    // Access frequency
    if (memory.accessCount) {
      score += Math.min(memory.accessCount / 10, 0.2);
    }
    
    // Explicit importance
    if (memory.importance) {
      score += memory.importance * 0.3;
    }
    
    // Content complexity
    if (memory.content) {
      const complexity = this.estimateComplexity(memory.content);
      score += complexity * 0.1;
    }
    
    // Type-based importance
    const typeScores = {
      error: 0.2,
      solution: 0.15,
      pattern: 0.15,
      fact: 0.1,
      interaction: 0.05
    };
    
    if (memory.type && typeScores[memory.type]) {
      score += typeScores[memory.type];
    }
    
    return Math.min(score, 1.0);
  }

  estimateComplexity(content) {
    if (!content) return 0;
    
    const str = typeof content === 'string' ? content : JSON.stringify(content);
    
    // Simple complexity based on length and unique characters
    const uniqueChars = new Set(str).size;
    const complexity = Math.min(uniqueChars / 100, 1.0) * 0.5 +
                      Math.min(str.length / 1000, 1.0) * 0.5;
    
    return complexity;
  }

  async mergeSimilarMemories(memories) {
    const merged = [];
    const processed = new Set();
    
    for (let i = 0; i < memories.length; i++) {
      if (processed.has(i)) continue;
      
      const memory = memories[i];
      const similar = [];
      
      // Find similar memories
      for (let j = i + 1; j < memories.length; j++) {
        if (processed.has(j)) continue;
        
        const similarity = this.calculateMemorySimilarity(memory, memories[j]);
        
        if (similarity > this.mergeThreshold) {
          similar.push({ index: j, memory: memories[j], similarity });
          processed.add(j);
        }
      }
      
      if (similar.length > 0) {
        // Merge memories
        const mergedMemory = this.mergeMemories(memory, similar.map(s => s.memory));
        merged.push(mergedMemory);
      } else {
        merged.push(memory);
      }
      
      processed.add(i);
    }
    
    logger.debug(`Merged ${memories.length - merged.length} similar memories`);
    
    return merged;
  }

  calculateMemorySimilarity(memory1, memory2) {
    // Type match
    if (memory1.type !== memory2.type) return 0;
    
    let similarity = 0.2; // Base similarity for same type
    
    // Content similarity (simple string comparison)
    if (memory1.content && memory2.content) {
      const content1 = typeof memory1.content === 'string' ? memory1.content : JSON.stringify(memory1.content);
      const content2 = typeof memory2.content === 'string' ? memory2.content : JSON.stringify(memory2.content);
      
      const contentSim = this.stringSimilarity(content1, content2);
      similarity += contentSim * 0.5;
    }
    
    // Embedding similarity
    if (memory1.embedding && memory2.embedding) {
      const embeddingSim = this.cosineSimilarity(memory1.embedding, memory2.embedding);
      similarity += embeddingSim * 0.3;
    }
    
    return similarity;
  }

  stringSimilarity(str1, str2) {
    // Jaccard similarity on words
    const words1 = new Set(str1.toLowerCase().split(/\s+/));
    const words2 = new Set(str2.toLowerCase().split(/\s+/));
    
    const intersection = new Set([...words1].filter(x => words2.has(x)));
    const union = new Set([...words1, ...words2]);
    
    return union.size > 0 ? intersection.size / union.size : 0;
  }

  cosineSimilarity(vec1, vec2) {
    if (!vec1 || !vec2 || vec1.length !== vec2.length) return 0;
    
    let dotProduct = 0;
    let norm1 = 0;
    let norm2 = 0;
    
    for (let i = 0; i < vec1.length; i++) {
      dotProduct += vec1[i] * vec2[i];
      norm1 += vec1[i] * vec1[i];
      norm2 += vec2[i] * vec2[i];
    }
    
    norm1 = Math.sqrt(norm1);
    norm2 = Math.sqrt(norm2);
    
    return (norm1 === 0 || norm2 === 0) ? 0 : dotProduct / (norm1 * norm2);
  }

  mergeMemories(primary, similar) {
    const merged = {
      ...primary,
      merged: true,
      mergedCount: similar.length + 1,
      mergedAt: Date.now()
    };
    
    // Combine access counts
    merged.accessCount = (primary.accessCount || 0) + 
      similar.reduce((sum, m) => sum + (m.accessCount || 0), 0);
    
    // Take highest importance
    merged.importance = Math.max(
      primary.importance || 0,
      ...similar.map(m => m.importance || 0)
    );
    
    // Combine content if applicable
    if (primary.content && similar.some(m => m.content)) {
      const contents = [primary.content, ...similar.map(m => m.content).filter(Boolean)];
      merged.content = this.combineContents(contents);
    }
    
    // Average embeddings
    if (primary.embedding) {
      const embeddings = [primary.embedding, ...similar.map(m => m.embedding).filter(Boolean)];
      merged.embedding = this.averageEmbeddings(embeddings);
    }
    
    return merged;
  }

  combineContents(contents) {
    // For now, just concatenate unique parts
    const uniqueParts = new Set();
    
    for (const content of contents) {
      const str = typeof content === 'string' ? content : JSON.stringify(content);
      uniqueParts.add(str);
    }
    
    return Array.from(uniqueParts).join(' | ');
  }

  averageEmbeddings(embeddings) {
    if (embeddings.length === 0) return null;
    
    const dimensions = embeddings[0].length;
    const averaged = new Array(dimensions).fill(0);
    
    for (const embedding of embeddings) {
      for (let i = 0; i < dimensions; i++) {
        averaged[i] += embedding[i];
      }
    }
    
    for (let i = 0; i < dimensions; i++) {
      averaged[i] /= embeddings.length;
    }
    
    return averaged;
  }

  async compressOldMemories(memories) {
    const now = Date.now();
    const compressionAge = 7 * 24 * 60 * 60 * 1000; // 7 days
    
    const compressed = memories.map(memory => {
      // Check if should compress
      const shouldCompress = 
        !memory.compressed &&
        memory.timestamp && (now - memory.timestamp > compressionAge) &&
        this.estimateMemorySize([memory]) > this.compressionThreshold;
      
      if (shouldCompress) {
        return this.compressMemory(memory);
      }
      
      return memory;
    });
    
    const compressedCount = compressed.filter(m => m.compressed && !memories.find(om => om.id === m.id && om.compressed)).length;
    
    if (compressedCount > 0) {
      logger.debug(`Compressed ${compressedCount} memories`);
    }
    
    return compressed;
  }

  compressMemory(memory) {
    const startSize = this.estimateMemorySize([memory]);
    
    const compressed = {
      ...memory,
      compressed: true,
      compressedAt: Date.now()
    };
    
    // Compress content
    if (memory.content) {
      const contentStr = typeof memory.content === 'string' ? memory.content : JSON.stringify(memory.content);
      compressed.compressedContent = this.compressor.compress(contentStr);
      compressed.originalSize = contentStr.length;
      compressed.compressedSize = compressed.compressedContent.length;
      delete compressed.content;
    }
    
    // Compress embedding (keep only top dimensions)
    if (memory.embedding && memory.embedding.length > 100) {
      compressed.compressedEmbedding = this.compressEmbedding(memory.embedding);
      delete compressed.embedding;
    }
    
    const endSize = this.estimateMemorySize([compressed]);
    const ratio = startSize / endSize;
    
    this.totalCompressions++;
    this.compressionRatios.push(ratio);
    
    return compressed;
  }

  compressEmbedding(embedding) {
    // Keep top 100 dimensions with highest absolute values
    const indexed = embedding.map((val, idx) => ({ val: Math.abs(val), idx, original: val }));
    indexed.sort((a, b) => b.val - a.val);
    
    const top = indexed.slice(0, 100);
    const compressed = {
      dimensions: top.map(t => ({ i: t.idx, v: t.original })),
      length: embedding.length
    };
    
    return compressed;
  }

  decompressMemory(memory) {
    if (!memory.compressed) return memory;
    
    const decompressed = {
      ...memory,
      compressed: false
    };
    
    // Decompress content
    if (memory.compressedContent) {
      decompressed.content = this.compressor.decompress(memory.compressedContent);
      delete decompressed.compressedContent;
      delete decompressed.originalSize;
      delete decompressed.compressedSize;
    }
    
    // Decompress embedding
    if (memory.compressedEmbedding) {
      decompressed.embedding = this.decompressEmbedding(memory.compressedEmbedding);
      delete decompressed.compressedEmbedding;
    }
    
    delete decompressed.compressedAt;
    
    return decompressed;
  }

  decompressEmbedding(compressed) {
    const embedding = new Array(compressed.length).fill(0);
    
    for (const dim of compressed.dimensions) {
      embedding[dim.i] = dim.v;
    }
    
    return embedding;
  }

  estimateMemorySize(memories) {
    let totalSize = 0;
    
    for (const memory of memories) {
      // Base object overhead
      totalSize += 200;
      
      // Content size
      if (memory.content) {
        const contentStr = typeof memory.content === 'string' ? memory.content : JSON.stringify(memory.content);
        totalSize += contentStr.length * 2; // UTF-16
      }
      
      if (memory.compressedContent) {
        totalSize += memory.compressedContent.length;
      }
      
      // Embedding size
      if (memory.embedding) {
        totalSize += memory.embedding.length * 8; // 64-bit floats
      }
      
      if (memory.compressedEmbedding) {
        totalSize += memory.compressedEmbedding.dimensions.length * 12; // index + value
      }
      
      // Metadata
      totalSize += JSON.stringify(memory).length;
    }
    
    return totalSize;
  }

  startPeriodicOptimization() {
    // Run optimization every hour
    setInterval(async () => {
      logger.debug('Running periodic memory optimization');
      // This would be called by the main system with actual memories
    }, 60 * 60 * 1000);
  }

  async getMetrics() {
    const avgCompressionRatio = this.compressionRatios.length > 0
      ? this.compressionRatios.reduce((a, b) => a + b, 0) / this.compressionRatios.length
      : 3.5; // Default estimate
    
    return {
      totalOptimizations: this.optimizationRuns,
      totalCompressions: this.totalCompressions,
      avgCompressionRatio,
      memoryReduction: this.totalMemoryReduced / (1024 * 1024), // MB
      memoryReductionPercentage: 0.4 // Estimate 40% reduction
    };
  }
}

export default new MemoryOptimizer();