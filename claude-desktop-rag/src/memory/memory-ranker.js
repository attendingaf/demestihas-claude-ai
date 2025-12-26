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

class MemoryRanker {
  constructor() {
    this.weights = {
      similarity: 0.4,
      recency: 0.2,
      relevance: 0.2,
      importance: 0.1,
      success: 0.1
    };
  }

  /**
   * Rank memories by multiple factors
   */
  rank(memories, query, options = {}) {
    const {
      weights = this.weights,
      contextWindow = 7 * 24 * 3600 * 1000, // 7 days
      projectContext = config.project.id
    } = options;

    const now = Date.now();
    const ranked = memories.map(memory => {
      const scores = {
        similarity: memory.similarity || memory.score || 0,
        recency: this.calculateRecencyScore(memory, now, contextWindow),
        relevance: this.calculateRelevanceScore(memory, query, projectContext),
        importance: this.calculateImportanceScore(memory),
        success: memory.success_score || 1.0
      };

      const totalScore = Object.keys(scores).reduce((sum, key) => {
        return sum + (scores[key] * weights[key]);
      }, 0);

      return {
        ...memory,
        scores,
        totalScore
      };
    });

    return ranked.sort((a, b) => b.totalScore - a.totalScore);
  }

  /**
   * Calculate recency score
   */
  calculateRecencyScore(memory, now, contextWindow) {
    const age = now - new Date(memory.created_at).getTime();
    
    if (age < 0) return 1.0; // Future date (error), treat as very recent
    if (age > contextWindow) return 0.1; // Outside context window
    
    // Exponential decay
    return Math.exp(-age / (contextWindow / 4));
  }

  /**
   * Calculate relevance score based on context
   */
  calculateRelevanceScore(memory, query, projectContext) {
    let score = 0.5; // Base score

    // Boost if same project
    if (memory.project_id === projectContext) {
      score += 0.2;
    }

    // Boost if has file paths
    if (memory.file_paths && memory.file_paths.length > 0) {
      score += 0.1;
    }

    // Boost if has tool chain
    if (memory.tool_chain && memory.tool_chain.length > 0) {
      score += 0.1;
    }

    // Check for keyword matches
    const keywords = this.extractKeywords(query);
    const contentKeywords = this.extractKeywords(memory.content);
    const overlap = this.calculateKeywordOverlap(keywords, contentKeywords);
    score += overlap * 0.1;

    return Math.min(1.0, score);
  }

  /**
   * Calculate importance score
   */
  calculateImportanceScore(memory) {
    let score = 0.5; // Base score

    // Boost for specific interaction types
    const importantTypes = ['error', 'bug_fix', 'implementation', 'architecture'];
    if (importantTypes.includes(memory.interaction_type)) {
      score += 0.3;
    }

    // Boost if has metadata flags
    if (memory.metadata) {
      if (memory.metadata.important) score += 0.2;
      if (memory.metadata.starred) score += 0.1;
      if (memory.metadata.pinned) score += 0.2;
    }

    return Math.min(1.0, score);
  }

  /**
   * Extract keywords from text
   */
  extractKeywords(text) {
    if (!text) return new Set();
    
    // Simple keyword extraction (could be enhanced with NLP)
    const words = text.toLowerCase()
      .replace(/[^\w\s]/g, ' ')
      .split(/\s+/)
      .filter(word => word.length > 3);
    
    return new Set(words);
  }

  /**
   * Calculate keyword overlap
   */
  calculateKeywordOverlap(set1, set2) {
    if (set1.size === 0 || set2.size === 0) return 0;
    
    const intersection = new Set([...set1].filter(x => set2.has(x)));
    const union = new Set([...set1, ...set2]);
    
    return intersection.size / union.size;
  }

  /**
   * Re-rank based on user feedback
   */
  rerank(memories, feedback) {
    const { useful, notUseful } = feedback;

    return memories.map(memory => {
      let adjustedScore = memory.totalScore || memory.score || memory.similarity;

      if (useful && useful.includes(memory.id)) {
        adjustedScore *= 1.5; // Boost useful memories
      }

      if (notUseful && notUseful.includes(memory.id)) {
        adjustedScore *= 0.5; // Penalize not useful memories
      }

      return {
        ...memory,
        adjustedScore
      };
    }).sort((a, b) => b.adjustedScore - a.adjustedScore);
  }

  /**
   * Group memories by similarity
   */
  groupBySimilarity(memories, threshold = 0.85) {
    const groups = [];
    const used = new Set();

    for (const memory of memories) {
      if (used.has(memory.id)) continue;

      const group = [memory];
      used.add(memory.id);

      // Find similar memories
      for (const other of memories) {
        if (used.has(other.id)) continue;
        
        if (this.calculateContentSimilarity(memory.content, other.content) > threshold) {
          group.push(other);
          used.add(other.id);
        }
      }

      groups.push({
        representative: memory,
        members: group,
        size: group.length
      });
    }

    return groups;
  }

  /**
   * Calculate content similarity (simple version)
   */
  calculateContentSimilarity(content1, content2) {
    const keywords1 = this.extractKeywords(content1);
    const keywords2 = this.extractKeywords(content2);
    return this.calculateKeywordOverlap(keywords1, keywords2);
  }

  /**
   * Diversify results to avoid redundancy
   */
  diversify(memories, maxSimilarity = 0.9) {
    if (memories.length <= 1) return memories;

    const diverse = [memories[0]];
    
    for (let i = 1; i < memories.length; i++) {
      const candidate = memories[i];
      let tooSimilar = false;

      for (const selected of diverse) {
        const similarity = this.calculateContentSimilarity(
          candidate.content,
          selected.content
        );

        if (similarity > maxSimilarity) {
          tooSimilar = true;
          break;
        }
      }

      if (!tooSimilar) {
        diverse.push(candidate);
      }
    }

    return diverse;
  }

  /**
   * Update ranking weights
   */
  updateWeights(newWeights) {
    this.weights = {
      ...this.weights,
      ...newWeights
    };

    // Normalize weights to sum to 1
    const sum = Object.values(this.weights).reduce((a, b) => a + b, 0);
    if (sum > 0) {
      Object.keys(this.weights).forEach(key => {
        this.weights[key] /= sum;
      });
    }

    logger.info('Ranking weights updated', this.weights);
  }

  /**
   * Get current weights
   */
  getWeights() {
    return { ...this.weights };
  }
}

export default new MemoryRanker();