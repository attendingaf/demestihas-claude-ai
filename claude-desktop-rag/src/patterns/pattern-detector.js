import crypto from 'crypto';
import winston from 'winston';
import embeddingService from '../core/embedding-service.js';
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

class PatternDetector {
  constructor() {
    this.recentInteractions = [];
    this.maxRecentSize = 100;
    this.detectionInterval = null;
  }

  /**
   * Initialize pattern detector
   */
  async initialize() {
    // Start periodic pattern detection
    this.detectionInterval = setInterval(() => {
      this.detectPatterns();
    }, 60000); // Check every minute

    logger.info('Pattern detector initialized');
  }

  /**
   * Record an interaction for pattern detection
   */
  async recordInteraction(interaction) {
    const record = {
      timestamp: Date.now(),
      content: interaction.content,
      toolChain: interaction.toolChain || [],
      filePaths: interaction.filePaths || [],
      success: interaction.success !== false,
      metadata: interaction.metadata || {}
    };

    this.recentInteractions.push(record);

    // Maintain size limit
    if (this.recentInteractions.length > this.maxRecentSize) {
      this.recentInteractions.shift();
    }

    // Check for immediate pattern
    await this.checkForPattern(record);
  }

  /**
   * Check if interaction matches existing patterns
   */
  async checkForPattern(interaction) {
    try {
      // Generate embedding for the interaction
      const embedding = await embeddingService.generateEmbedding(interaction.content);

      // Search for similar patterns
      const patterns = await this.findSimilarPatterns(embedding);

      for (const pattern of patterns) {
        const similarity = embeddingService.cosineSimilarity(
          embedding,
          pattern.trigger_embedding
        );

        if (similarity >= config.rag.patternThreshold) {
          await this.updatePatternOccurrence(pattern, interaction, similarity);
        }
      }

      // Check if this forms a new pattern
      await this.detectNewPattern(interaction, embedding);
    } catch (error) {
      logger.error('Failed to check for pattern', { error: error.message });
    }
  }

  /**
   * Detect new patterns from recent interactions
   */
  async detectNewPattern(interaction, embedding) {
    const timeWindow = config.rag.patternTimeWindowDays * 24 * 3600 * 1000;
    const cutoff = Date.now() - timeWindow;

    // Filter recent interactions within time window
    const recent = this.recentInteractions.filter(i => i.timestamp > cutoff);

    // Group similar interactions
    const similar = [];
    for (const other of recent) {
      if (other === interaction) continue;

      const otherEmbedding = await embeddingService.generateEmbedding(other.content);
      const similarity = embeddingService.cosineSimilarity(embedding, otherEmbedding);

      if (similarity >= config.rag.patternThreshold) {
        similar.push({
          interaction: other,
          similarity
        });
      }
    }

    // Check if we have enough occurrences
    if (similar.length >= config.rag.patternMinOccurrences - 1) {
      await this.createPattern(interaction, similar, embedding);
    }
  }

  /**
   * Create a new pattern
   */
  async createPattern(trigger, similar, embedding) {
    try {
      // Extract common elements
      const commonTools = this.extractCommonElements(
        [trigger, ...similar.map(s => s.interaction)],
        'toolChain'
      );

      const commonPaths = this.extractCommonElements(
        [trigger, ...similar.map(s => s.interaction)],
        'filePaths'
      );

      // Generate pattern hash
      const patternHash = this.generatePatternHash(trigger.content, commonTools);

      // Create pattern object
      const pattern = {
        id: crypto.randomUUID(),
        pattern_hash: patternHash,
        pattern_name: this.generatePatternName(trigger, commonTools),
        trigger_embedding: embedding,
        action_sequence: {
          tools: commonTools,
          paths: commonPaths,
          template: this.extractTemplate(trigger, similar)
        },
        occurrence_count: similar.length + 1,
        success_rate: this.calculateSuccessRate([trigger, ...similar.map(s => s.interaction)]),
        last_used: new Date().toISOString(),
        project_contexts: [config.project.id],
        auto_apply: false
      };

      // Store pattern
      await sqliteClient.storePattern(pattern);
      await supabaseClient.storePattern(pattern);

      logger.info('New pattern detected and stored', {
        name: pattern.pattern_name,
        occurrences: pattern.occurrence_count
      });
    } catch (error) {
      logger.error('Failed to create pattern', { error: error.message });
    }
  }

  /**
   * Update existing pattern occurrence
   */
  async updatePatternOccurrence(pattern, interaction, similarity) {
    try {
      pattern.occurrence_count += 1;
      pattern.last_used = new Date().toISOString();

      // Update success rate
      if (interaction.success) {
        pattern.success_rate = (
          (pattern.success_rate * (pattern.occurrence_count - 1)) + 1
        ) / pattern.occurrence_count;
      } else {
        pattern.success_rate = (
          pattern.success_rate * (pattern.occurrence_count - 1)
        ) / pattern.occurrence_count;
      }

      // Enable auto-apply if criteria met
      if (
        pattern.occurrence_count >= 5 &&
        pattern.success_rate >= 0.9 &&
        !pattern.auto_apply
      ) {
        pattern.auto_apply = true;
        logger.info('Pattern auto-apply enabled', {
          name: pattern.pattern_name,
          successRate: pattern.success_rate
        });
      }

      // Update pattern in storage
      await sqliteClient.storePattern(pattern);
      await supabaseClient.storePattern(pattern);

      logger.debug('Pattern occurrence updated', {
        name: pattern.pattern_name,
        count: pattern.occurrence_count
      });
    } catch (error) {
      logger.error('Failed to update pattern occurrence', { error: error.message });
    }
  }

  /**
   * Find similar patterns
   */
  async findSimilarPatterns(embedding) {
    try {
      const [localPatterns, cloudPatterns] = await Promise.all([
        this.searchLocalPatterns(embedding),
        this.searchCloudPatterns(embedding)
      ]);

      return this.mergePatterns(localPatterns, cloudPatterns);
    } catch (error) {
      logger.error('Failed to find similar patterns', { error: error.message });
      return [];
    }
  }

  /**
   * Search local patterns
   */
  async searchLocalPatterns(embedding) {
    // Implementation for SQLite pattern search
    return [];
  }

  /**
   * Search cloud patterns
   */
  async searchCloudPatterns(embedding) {
    return supabaseClient.searchPatterns(embedding);
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

    return merged;
  }

  /**
   * Extract common elements from interactions
   */
  extractCommonElements(interactions, field) {
    if (interactions.length === 0) return [];

    const counts = new Map();

    for (const interaction of interactions) {
      const elements = interaction[field] || [];
      for (const element of elements) {
        counts.set(element, (counts.get(element) || 0) + 1);
      }
    }

    // Return elements that appear in most interactions
    const threshold = interactions.length * 0.7;
    return Array.from(counts.entries())
      .filter(([_, count]) => count >= threshold)
      .map(([element, _]) => element);
  }

  /**
   * Generate pattern hash
   */
  generatePatternHash(content, tools) {
    const data = JSON.stringify({ content: content.substring(0, 100), tools });
    return crypto.createHash('sha256').update(data).digest('hex');
  }

  /**
   * Generate pattern name
   */
  generatePatternName(trigger, tools) {
    const action = trigger.content.split(' ')[0].toLowerCase();
    const toolStr = tools.length > 0 ? `_${tools[0]}` : '';
    return `${action}${toolStr}_pattern_${Date.now()}`;
  }

  /**
   * Extract template from similar interactions
   */
  extractTemplate(trigger, similar) {
    // Simple template extraction (could be enhanced)
    return {
      trigger: trigger.content.substring(0, 200),
      variations: similar.slice(0, 3).map(s => 
        s.interaction.content.substring(0, 200)
      )
    };
  }

  /**
   * Calculate success rate
   */
  calculateSuccessRate(interactions) {
    const successful = interactions.filter(i => i.success !== false).length;
    return successful / interactions.length;
  }

  /**
   * Periodic pattern detection
   */
  async detectPatterns() {
    try {
      const timeWindow = config.rag.patternTimeWindowDays * 24 * 3600 * 1000;
      const cutoff = Date.now() - timeWindow;

      // Group recent interactions
      const recent = this.recentInteractions.filter(i => i.timestamp > cutoff);
      
      if (recent.length < config.rag.patternMinOccurrences) {
        return;
      }

      // Find clusters of similar interactions
      const clusters = await this.clusterInteractions(recent);

      // Create patterns from significant clusters
      for (const cluster of clusters) {
        if (cluster.length >= config.rag.patternMinOccurrences) {
          const embedding = await embeddingService.generateEmbedding(
            cluster[0].content
          );
          await this.createPattern(cluster[0], cluster.slice(1), embedding);
        }
      }
    } catch (error) {
      logger.error('Failed to detect patterns', { error: error.message });
    }
  }

  /**
   * Cluster similar interactions
   */
  async clusterInteractions(interactions) {
    const clusters = [];
    const used = new Set();

    for (const interaction of interactions) {
      if (used.has(interaction)) continue;

      const cluster = [interaction];
      used.add(interaction);

      const embedding = await embeddingService.generateEmbedding(interaction.content);

      for (const other of interactions) {
        if (used.has(other)) continue;

        const otherEmbedding = await embeddingService.generateEmbedding(other.content);
        const similarity = embeddingService.cosineSimilarity(embedding, otherEmbedding);

        if (similarity >= config.rag.patternThreshold) {
          cluster.push(other);
          used.add(other);
        }
      }

      if (cluster.length >= config.rag.patternMinOccurrences) {
        clusters.push(cluster);
      }
    }

    return clusters;
  }

  /**
   * Stop pattern detection
   */
  stop() {
    if (this.detectionInterval) {
      clearInterval(this.detectionInterval);
      this.detectionInterval = null;
    }
  }
}

export default new PatternDetector();