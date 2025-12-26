import winston from 'winston';
import { config } from '../../config/rag-config.js';
import sqliteClient from '../core/sqlite-client-optimized.js';
import projectContextManager from './project-context-manager.js';

const logger = winston.createLogger({
  level: config.logging.level,
  format: winston.format.json(),
  transports: [
    new winston.transports.Console(),
    new winston.transports.File({ filename: config.logging.file })
  ]
});

const PRIORITY_LEVELS = {
  CURRENT_CONTEXT: {
    level: 1,
    boost: 2.0,
    description: 'Current file/function context'
  },
  RECENT_INTERACTION: {
    level: 2,
    boost: 1.5,
    description: 'Recent interactions within 1 hour'
  },
  PROJECT_PATTERN: {
    level: 3,
    boost: 1.3,
    description: 'Project-specific patterns'
  },
  TEAM_KNOWLEDGE: {
    level: 4,
    boost: 1.1,
    description: 'Team shared knowledge'
  },
  GLOBAL_PATTERN: {
    level: 5,
    boost: 1.0,
    description: 'Global patterns and knowledge'
  }
};

class ContextPrioritizer {
  constructor() {
    this.currentContext = {
      file: null,
      function: null,
      timestamp: null
    };
    this.recentInteractions = [];
    this.contextWindow = 60 * 60 * 1000; // 1 hour
    this.priorityMetrics = {
      boostApplications: {},
      avgBoost: 1.0,
      totalPrioritizations: 0
    };
  }

  async initialize() {
    try {
      // Initialize project context manager
      await projectContextManager.initialize();
      
      // Load recent interactions
      await this.loadRecentInteractions();
      
      logger.info('Context Prioritizer initialized');
    } catch (error) {
      logger.error('Failed to initialize Context Prioritizer', { 
        error: error.message 
      });
      throw error;
    }
  }

  setCurrentContext(file, functionName = null) {
    this.currentContext = {
      file,
      function: functionName,
      timestamp: Date.now()
    };
    
    logger.debug('Current context updated', { 
      file, 
      function: functionName 
    });
  }

  async prioritizeResults(results, query, options = {}) {
    const startTime = Date.now();
    
    const {
      includePatterns = true,
      projectId = config.project.id,
      contextFile = this.currentContext.file,
      contextFunction = this.currentContext.function
    } = options;

    try {
      // Get project context
      const projectContext = await projectContextManager.getContextForQuery(
        query, 
        projectId
      );

      // Apply priority boosts to each result
      const prioritizedResults = await Promise.all(
        results.map(async (result) => {
          const priorityScore = await this.calculatePriorityScore(
            result,
            query,
            {
              contextFile,
              contextFunction,
              projectContext
            }
          );

          return {
            ...result,
            priorityScore,
            originalSimilarity: result.similarity,
            boostedSimilarity: result.similarity * priorityScore.totalBoost
          };
        })
      );

      // Sort by boosted similarity
      prioritizedResults.sort((a, b) => 
        b.boostedSimilarity - a.boostedSimilarity
      );

      // Add relevant patterns if requested
      if (includePatterns) {
        const patterns = await this.getPrioritizedPatterns(
          query,
          projectContext
        );
        prioritizedResults.patterns = patterns;
      }

      // Track metrics
      this.trackPrioritizationMetrics(prioritizedResults);
      
      logger.debug('Results prioritized', {
        count: prioritizedResults.length,
        time: Date.now() - startTime
      });

      return prioritizedResults;
    } catch (error) {
      logger.error('Failed to prioritize results', { 
        error: error.message 
      });
      return results; // Return unprioritized on error
    }
  }

  async calculatePriorityScore(result, query, context) {
    const score = {
      levels: [],
      totalBoost: 1.0,
      breakdown: {}
    };

    // Level 1: Current file/function context
    if (this.isCurrentContext(result, context)) {
      score.levels.push(PRIORITY_LEVELS.CURRENT_CONTEXT);
      score.totalBoost *= PRIORITY_LEVELS.CURRENT_CONTEXT.boost;
      score.breakdown.currentContext = PRIORITY_LEVELS.CURRENT_CONTEXT.boost;
    }

    // Level 2: Recent interactions
    if (this.isRecentInteraction(result)) {
      const recencyBoost = this.calculateRecencyBoost(result);
      score.levels.push(PRIORITY_LEVELS.RECENT_INTERACTION);
      score.totalBoost *= recencyBoost;
      score.breakdown.recentInteraction = recencyBoost;
    }

    // Level 3: Project patterns
    if (await this.isProjectPattern(result, context.projectContext)) {
      score.levels.push(PRIORITY_LEVELS.PROJECT_PATTERN);
      score.totalBoost *= PRIORITY_LEVELS.PROJECT_PATTERN.boost;
      score.breakdown.projectPattern = PRIORITY_LEVELS.PROJECT_PATTERN.boost;
    }

    // Level 4: Team knowledge
    if (this.isTeamKnowledge(result)) {
      score.levels.push(PRIORITY_LEVELS.TEAM_KNOWLEDGE);
      score.totalBoost *= PRIORITY_LEVELS.TEAM_KNOWLEDGE.boost;
      score.breakdown.teamKnowledge = PRIORITY_LEVELS.TEAM_KNOWLEDGE.boost;
    }

    // Apply contextual modifiers
    const contextModifier = await this.calculateContextModifier(
      result,
      query,
      context
    );
    score.totalBoost *= contextModifier;
    score.breakdown.contextModifier = contextModifier;

    return score;
  }

  isCurrentContext(result, context) {
    if (!context.contextFile) return false;

    // Check if result is from current file
    if (result.file_paths && Array.isArray(result.file_paths)) {
      const isCurrentFile = result.file_paths.some(path => 
        path === context.contextFile || 
        path.endsWith(context.contextFile)
      );

      if (isCurrentFile) {
        // Extra boost if also in current function
        if (context.contextFunction && result.metadata) {
          const metadata = typeof result.metadata === 'string' ? 
            JSON.parse(result.metadata) : result.metadata;
          
          if (metadata.function === context.contextFunction) {
            return true;
          }
        }
        return true;
      }
    }

    return false;
  }

  isRecentInteraction(result) {
    const now = Date.now();
    const resultTime = result.last_accessed ? 
      result.last_accessed * 1000 : 
      result.created_at * 1000;

    return (now - resultTime) < this.contextWindow;
  }

  calculateRecencyBoost(result) {
    const now = Date.now();
    const resultTime = result.last_accessed ? 
      result.last_accessed * 1000 : 
      result.created_at * 1000;
    
    const age = now - resultTime;
    
    if (age < 5 * 60 * 1000) { // Less than 5 minutes
      return 1.5;
    } else if (age < 15 * 60 * 1000) { // Less than 15 minutes
      return 1.4;
    } else if (age < 30 * 60 * 1000) { // Less than 30 minutes
      return 1.3;
    } else if (age < this.contextWindow) { // Less than 1 hour
      return 1.2;
    }
    
    return 1.0;
  }

  async isProjectPattern(result, projectContext) {
    if (!projectContext || !projectContext.patterns) return false;

    // Check if result matches any project patterns
    const patterns = projectContext.patterns;
    
    for (const pattern of patterns) {
      if (this.matchesPattern(result, pattern)) {
        return true;
      }
    }

    return false;
  }

  matchesPattern(result, pattern) {
    // Check if result content matches pattern trigger
    if (pattern.trigger_embedding && result.embedding) {
      const similarity = sqliteClient.cosineSimilarity(
        result.embedding,
        pattern.trigger_embedding
      );
      
      if (similarity > 0.8) {
        return true;
      }
    }

    // Check if result matches pattern action sequence
    if (pattern.action_sequence && result.tool_chain) {
      const resultTools = Array.isArray(result.tool_chain) ? 
        result.tool_chain : 
        JSON.parse(result.tool_chain || '[]');
      
      const patternTools = Array.isArray(pattern.action_sequence) ?
        pattern.action_sequence :
        JSON.parse(pattern.action_sequence || '[]');
      
      if (this.sequenceMatches(resultTools, patternTools)) {
        return true;
      }
    }

    return false;
  }

  sequenceMatches(sequence1, sequence2) {
    if (sequence1.length !== sequence2.length) return false;
    
    for (let i = 0; i < sequence1.length; i++) {
      if (sequence1[i] !== sequence2[i]) {
        return false;
      }
    }
    
    return true;
  }

  isTeamKnowledge(result) {
    // Check if result is marked as team knowledge
    if (result.metadata) {
      const metadata = typeof result.metadata === 'string' ? 
        JSON.parse(result.metadata) : result.metadata;
      
      if (metadata.isTeamKnowledge || metadata.sharedBy) {
        return true;
      }
    }

    // Check if result has been accessed by multiple users
    if (result.access_count && result.access_count > 5) {
      return true;
    }

    return false;
  }

  async calculateContextModifier(result, query, context) {
    let modifier = 1.0;

    // Boost if result has high success score
    if (result.success_score && result.success_score > 0.8) {
      modifier *= 1.1;
    }

    // Boost if result has been frequently accessed
    if (result.access_count) {
      if (result.access_count > 10) {
        modifier *= 1.15;
      } else if (result.access_count > 5) {
        modifier *= 1.08;
      }
    }

    // Boost if result matches current project language/framework
    if (context.projectContext && context.projectContext.settings) {
      const settings = context.projectContext.settings;
      
      if (settings.language && result.metadata) {
        const metadata = typeof result.metadata === 'string' ? 
          JSON.parse(result.metadata) : result.metadata;
        
        if (metadata.language === settings.language) {
          modifier *= 1.1;
        }
      }
    }

    // Penalize if result is marked as deprecated
    if (result.metadata) {
      const metadata = typeof result.metadata === 'string' ? 
        JSON.parse(result.metadata) : result.metadata;
      
      if (metadata.deprecated) {
        modifier *= 0.5;
      }
    }

    return modifier;
  }

  async getPrioritizedPatterns(query, projectContext) {
    if (!projectContext || !projectContext.patterns) return [];

    const patterns = projectContext.patterns;
    const prioritizedPatterns = [];

    for (const pattern of patterns) {
      const priority = this.calculatePatternPriority(pattern);
      
      prioritizedPatterns.push({
        ...pattern,
        priority,
        priorityLevel: this.getPatternPriorityLevel(priority)
      });
    }

    // Sort by priority
    prioritizedPatterns.sort((a, b) => b.priority - a.priority);

    return prioritizedPatterns.slice(0, 5); // Top 5 patterns
  }

  calculatePatternPriority(pattern) {
    let priority = 1.0;

    // Boost for high occurrence count
    if (pattern.occurrence_count > 10) {
      priority *= 1.5;
    } else if (pattern.occurrence_count > 5) {
      priority *= 1.2;
    }

    // Boost for high success rate
    if (pattern.success_rate > 0.9) {
      priority *= 1.3;
    } else if (pattern.success_rate > 0.7) {
      priority *= 1.1;
    }

    // Boost for recent usage
    if (pattern.last_used) {
      const age = Date.now() - (pattern.last_used * 1000);
      
      if (age < 24 * 60 * 60 * 1000) { // Less than 1 day
        priority *= 1.2;
      } else if (age < 7 * 24 * 60 * 60 * 1000) { // Less than 1 week
        priority *= 1.1;
      }
    }

    // Boost for auto-apply patterns
    if (pattern.auto_apply) {
      priority *= 1.2;
    }

    return priority;
  }

  getPatternPriorityLevel(priority) {
    if (priority > 2.0) return 'HIGH';
    if (priority > 1.5) return 'MEDIUM';
    return 'LOW';
  }

  async loadRecentInteractions() {
    const sql = `
      SELECT id, content, created_at, last_accessed
      FROM project_memories_cache
      WHERE project_id = ?
        AND (last_accessed > ? OR created_at > ?)
      ORDER BY last_accessed DESC, created_at DESC
      LIMIT 50
    `;

    const cutoff = Math.floor((Date.now() - this.contextWindow) / 1000);

    try {
      const rows = await sqliteClient.db.all(sql, [
        config.project.id,
        cutoff,
        cutoff
      ]);
      
      this.recentInteractions = rows.map(row => ({
        id: row.id,
        content: row.content,
        timestamp: Math.max(row.last_accessed, row.created_at) * 1000
      }));
      
      logger.debug('Recent interactions loaded', { 
        count: this.recentInteractions.length 
      });
    } catch (error) {
      logger.error('Failed to load recent interactions', { 
        error: error.message 
      });
      this.recentInteractions = [];
    }
  }

  trackPrioritizationMetrics(results) {
    this.priorityMetrics.totalPrioritizations++;

    // Track boost applications
    for (const result of results) {
      if (result.priorityScore) {
        for (const level of result.priorityScore.levels) {
          const levelName = level.description;
          
          if (!this.priorityMetrics.boostApplications[levelName]) {
            this.priorityMetrics.boostApplications[levelName] = 0;
          }
          
          this.priorityMetrics.boostApplications[levelName]++;
        }
      }
    }

    // Calculate average boost
    const totalBoost = results.reduce((sum, r) => 
      sum + (r.priorityScore?.totalBoost || 1.0), 0
    );
    
    this.priorityMetrics.avgBoost = results.length > 0 ? 
      totalBoost / results.length : 1.0;
  }

  async updateRecentInteractions(interaction) {
    // Add to recent interactions
    this.recentInteractions.unshift({
      id: interaction.id,
      content: interaction.content,
      timestamp: Date.now()
    });

    // Trim old interactions
    const cutoff = Date.now() - this.contextWindow;
    this.recentInteractions = this.recentInteractions.filter(i => 
      i.timestamp > cutoff
    );

    // Keep max 50 interactions
    if (this.recentInteractions.length > 50) {
      this.recentInteractions = this.recentInteractions.slice(0, 50);
    }
  }

  getMetrics() {
    return {
      currentContext: this.currentContext,
      recentInteractionCount: this.recentInteractions.length,
      contextWindow: this.contextWindow,
      priorityLevels: PRIORITY_LEVELS,
      metrics: this.priorityMetrics
    };
  }

  reset() {
    this.currentContext = {
      file: null,
      function: null,
      timestamp: null
    };
    this.recentInteractions = [];
    
    logger.debug('Context prioritizer reset');
  }
}

export default new ContextPrioritizer();