import winston from 'winston';
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

class PatternMatcher {
  constructor() {
    this.activePatterns = new Map();
    this.executionHistory = [];
    this.maxHistorySize = 100;
  }

  /**
   * Match query against available patterns
   */
  async match(query, patterns) {
    try {
      const queryEmbedding = await embeddingService.generateEmbedding(query);
      
      const matches = [];

      for (const pattern of patterns) {
        const similarity = embeddingService.cosineSimilarity(
          queryEmbedding,
          pattern.trigger_embedding
        );

        if (similarity >= config.rag.patternThreshold) {
          matches.push({
            pattern,
            similarity,
            confidence: this.calculateConfidence(pattern, similarity)
          });
        }
      }

      // Sort by confidence
      matches.sort((a, b) => b.confidence - a.confidence);

      logger.debug('Patterns matched', {
        query: query.substring(0, 50),
        matches: matches.length
      });

      return matches;
    } catch (error) {
      logger.error('Failed to match patterns', { error: error.message });
      return [];
    }
  }

  /**
   * Calculate pattern confidence
   */
  calculateConfidence(pattern, similarity) {
    // Base confidence from similarity
    let confidence = similarity;

    // Factor in success rate
    confidence *= pattern.success_rate || 1.0;

    // Factor in occurrence count (more occurrences = higher confidence)
    const occurrenceFactor = Math.min(1.0, pattern.occurrence_count / 10);
    confidence *= (0.7 + 0.3 * occurrenceFactor);

    // Factor in recency
    if (pattern.last_used) {
      const age = Date.now() - new Date(pattern.last_used).getTime();
      const recencyFactor = Math.exp(-age / (7 * 24 * 3600 * 1000)); // 7-day decay
      confidence *= (0.8 + 0.2 * recencyFactor);
    }

    return confidence;
  }

  /**
   * Apply a pattern to generate actions
   */
  async applyPattern(pattern, context = {}) {
    try {
      const execution = {
        patternId: pattern.id,
        patternName: pattern.pattern_name,
        timestamp: Date.now(),
        context,
        status: 'started'
      };

      this.activePatterns.set(pattern.id, execution);

      // Generate actions from pattern
      const actions = this.generateActions(pattern, context);

      // Validate actions
      const validated = await this.validateActions(actions, context);

      // Record execution
      execution.actions = validated;
      execution.status = 'completed';
      this.recordExecution(execution);

      logger.info('Pattern applied successfully', {
        pattern: pattern.pattern_name,
        actions: validated.length
      });

      return {
        success: true,
        actions: validated,
        pattern: pattern.pattern_name
      };
    } catch (error) {
      logger.error('Failed to apply pattern', {
        pattern: pattern.pattern_name,
        error: error.message
      });

      return {
        success: false,
        error: error.message,
        pattern: pattern.pattern_name
      };
    } finally {
      this.activePatterns.delete(pattern.id);
    }
  }

  /**
   * Generate actions from pattern
   */
  generateActions(pattern, context) {
    const actions = [];
    const sequence = pattern.action_sequence;

    if (sequence.tools && sequence.tools.length > 0) {
      for (const tool of sequence.tools) {
        actions.push({
          type: 'tool',
          tool: tool,
          parameters: this.interpolateParameters(tool, context)
        });
      }
    }

    if (sequence.paths && sequence.paths.length > 0) {
      for (const path of sequence.paths) {
        actions.push({
          type: 'file',
          path: this.interpolatePath(path, context),
          operation: 'process'
        });
      }
    }

    if (sequence.template) {
      actions.push({
        type: 'template',
        content: this.interpolateTemplate(sequence.template, context)
      });
    }

    return actions;
  }

  /**
   * Validate generated actions
   */
  async validateActions(actions, context) {
    const validated = [];

    for (const action of actions) {
      if (await this.isValidAction(action, context)) {
        validated.push(action);
      } else {
        logger.warn('Invalid action filtered', { action });
      }
    }

    return validated;
  }

  /**
   * Check if action is valid
   */
  async isValidAction(action, context) {
    switch (action.type) {
      case 'tool':
        return this.isValidTool(action.tool);
      
      case 'file':
        return this.isValidPath(action.path);
      
      case 'template':
        return action.content && action.content.length > 0;
      
      default:
        return false;
    }
  }

  /**
   * Check if tool is valid
   */
  isValidTool(tool) {
    const validTools = [
      'search', 'retrieve', 'store', 'analyze',
      'generate', 'transform', 'validate'
    ];
    return validTools.includes(tool);
  }

  /**
   * Check if path is valid
   */
  isValidPath(path) {
    // Basic path validation
    return path && path.length > 0 && !path.includes('..');
  }

  /**
   * Interpolate parameters with context
   */
  interpolateParameters(tool, context) {
    const params = {};

    switch (tool) {
      case 'search':
        params.query = context.query || '';
        params.limit = context.limit || 10;
        break;
      
      case 'retrieve':
        params.id = context.targetId || null;
        break;
      
      case 'store':
        params.content = context.content || '';
        params.metadata = context.metadata || {};
        break;
      
      default:
        break;
    }

    return params;
  }

  /**
   * Interpolate path with context
   */
  interpolatePath(path, context) {
    let interpolated = path;

    // Replace placeholders
    if (context.projectPath) {
      interpolated = interpolated.replace('${project}', context.projectPath);
    }
    if (context.fileName) {
      interpolated = interpolated.replace('${file}', context.fileName);
    }

    return interpolated;
  }

  /**
   * Interpolate template with context
   */
  interpolateTemplate(template, context) {
    let content = template.trigger || '';

    // Replace placeholders with context values
    Object.keys(context).forEach(key => {
      const placeholder = `\${${key}}`;
      if (content.includes(placeholder)) {
        content = content.replace(new RegExp(placeholder, 'g'), context[key]);
      }
    });

    return content;
  }

  /**
   * Record pattern execution
   */
  recordExecution(execution) {
    this.executionHistory.push(execution);

    // Maintain size limit
    if (this.executionHistory.length > this.maxHistorySize) {
      this.executionHistory.shift();
    }
  }

  /**
   * Get pattern execution history
   */
  getExecutionHistory(patternId = null) {
    if (patternId) {
      return this.executionHistory.filter(e => e.patternId === patternId);
    }
    return [...this.executionHistory];
  }

  /**
   * Get active patterns
   */
  getActivePatterns() {
    return Array.from(this.activePatterns.values());
  }

  /**
   * Suggest patterns for context
   */
  async suggestPatterns(context, availablePatterns) {
    const suggestions = [];

    for (const pattern of availablePatterns) {
      // Check if pattern is applicable to context
      if (this.isApplicable(pattern, context)) {
        const score = this.scorePattern(pattern, context);
        
        suggestions.push({
          pattern,
          score,
          reason: this.explainSuggestion(pattern, context)
        });
      }
    }

    // Sort by score
    suggestions.sort((a, b) => b.score - a.score);

    return suggestions.slice(0, 5); // Top 5 suggestions
  }

  /**
   * Check if pattern is applicable
   */
  isApplicable(pattern, context) {
    // Check project context
    if (pattern.project_contexts && pattern.project_contexts.length > 0) {
      if (!pattern.project_contexts.includes(context.projectId)) {
        return false;
      }
    }

    // Check required tools
    if (pattern.action_sequence.tools) {
      for (const tool of pattern.action_sequence.tools) {
        if (!this.isValidTool(tool)) {
          return false;
        }
      }
    }

    return true;
  }

  /**
   * Score pattern for context
   */
  scorePattern(pattern, context) {
    let score = 0;

    // Success rate component
    score += pattern.success_rate * 0.4;

    // Occurrence count component
    score += Math.min(1.0, pattern.occurrence_count / 20) * 0.3;

    // Recency component
    if (pattern.last_used) {
      const age = Date.now() - new Date(pattern.last_used).getTime();
      const recency = Math.exp(-age / (14 * 24 * 3600 * 1000)); // 14-day decay
      score += recency * 0.2;
    }

    // Auto-apply bonus
    if (pattern.auto_apply) {
      score += 0.1;
    }

    return score;
  }

  /**
   * Explain why pattern was suggested
   */
  explainSuggestion(pattern, context) {
    const reasons = [];

    if (pattern.success_rate > 0.9) {
      reasons.push(`High success rate (${(pattern.success_rate * 100).toFixed(0)}%)`);
    }

    if (pattern.occurrence_count > 10) {
      reasons.push(`Frequently used (${pattern.occurrence_count} times)`);
    }

    if (pattern.auto_apply) {
      reasons.push('Auto-apply enabled');
    }

    const age = Date.now() - new Date(pattern.last_used).getTime();
    if (age < 24 * 3600 * 1000) {
      reasons.push('Recently used');
    }

    return reasons.join(', ') || 'Matches context';
  }
}

export default new PatternMatcher();