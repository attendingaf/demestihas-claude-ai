import winston from 'winston';
import { performance } from 'perf_hooks';
import { config } from '../../config/rag-config.js';
import episodicMemory from '../memory/advanced/episodic-memory.js';
import semanticClusterer from '../memory/advanced/semantic-clusterer.js';
import persistentMemory from '../memory/advanced/persistent-memory.js';

const logger = winston.createLogger({
  level: config.logging.level,
  format: winston.format.json(),
  transports: [
    new winston.transports.Console(),
    new winston.transports.File({ filename: config.logging.file })
  ]
});

class SuggestionEngine {
  constructor() {
    this.suggestions = new Map();
    this.patternThreshold = 3; // Min occurrences for pattern-based suggestions
    this.confidenceThreshold = 0.6;
    this.maxSuggestions = 5;
    this.contextWindow = 5; // Recent actions to consider
    this.suggestionCache = new Map();
    this.cacheTimeout = 60000; // 1 minute
    this.metrics = {
      totalSuggestions: 0,
      acceptedSuggestions: 0,
      rejectedSuggestions: 0,
      avgGenerationTime: 0,
      patternBasedSuggestions: 0,
      contextBasedSuggestions: 0
    };
  }

  async initialize() {
    logger.info('Initializing suggestion engine...');
    await this.loadUserPatterns();
    logger.info('Suggestion engine initialized');
  }

  async generateSuggestions(currentContext) {
    const startTime = performance.now();
    
    // Check cache
    const cacheKey = this.getCacheKey(currentContext);
    const cached = this.suggestionCache.get(cacheKey);
    if (cached && Date.now() - cached.timestamp < this.cacheTimeout) {
      logger.debug('Using cached suggestions');
      return cached.suggestions;
    }
    
    try {
      // Get recent episodes for context
      const recentEpisodes = await episodicMemory.recallEpisodes({
        timeWindow: 'recent',
        limit: this.contextWindow
      });
      
      // Get user preferences
      const userContext = await this.getUserContext(currentContext.userId);
      
      // Generate different types of suggestions
      const [
        patternSuggestions,
        clusterSuggestions,
        contextSuggestions,
        historicalSuggestions
      ] = await Promise.all([
        this.generatePatternBasedSuggestions(recentEpisodes, userContext),
        this.generateClusterBasedSuggestions(currentContext),
        this.generateContextualSuggestions(currentContext, recentEpisodes),
        this.generateHistoricalSuggestions(currentContext, userContext)
      ]);
      
      // Combine and rank suggestions
      const allSuggestions = [
        ...patternSuggestions,
        ...clusterSuggestions,
        ...contextSuggestions,
        ...historicalSuggestions
      ];
      
      // Deduplicate and score
      const scoredSuggestions = this.scoreSuggestions(allSuggestions, currentContext);
      
      // Filter by confidence and limit
      const finalSuggestions = scoredSuggestions
        .filter(s => s.confidence >= this.confidenceThreshold)
        .sort((a, b) => b.confidence - a.confidence)
        .slice(0, this.maxSuggestions);
      
      // Update metrics
      const generationTime = performance.now() - startTime;
      this.updateMetrics(finalSuggestions, generationTime);
      
      // Cache results
      this.suggestionCache.set(cacheKey, {
        suggestions: finalSuggestions,
        timestamp: Date.now()
      });
      
      logger.debug('Generated suggestions', {
        count: finalSuggestions.length,
        time: `${generationTime.toFixed(2)}ms`
      });
      
      return finalSuggestions;
    } catch (error) {
      logger.error('Failed to generate suggestions', { error: error.message });
      return [];
    }
  }

  async generatePatternBasedSuggestions(recentEpisodes, userContext) {
    const suggestions = [];
    
    if (!userContext.patterns || userContext.patterns.length === 0) {
      return suggestions;
    }
    
    // Analyze recent episode sequence
    const recentSequence = recentEpisodes.map(e => e.event?.type).filter(Boolean).join('->');
    
    for (const pattern of userContext.patterns) {
      if (pattern.frequency >= this.patternThreshold) {
        // Check if current sequence matches pattern prefix
        if (pattern.pattern.startsWith(recentSequence)) {
          const nextAction = this.extractNextAction(pattern.pattern, recentSequence);
          if (nextAction) {
            suggestions.push({
              type: 'pattern',
              action: nextAction,
              reason: `Based on pattern: ${pattern.pattern} (${pattern.frequency} occurrences)`,
              confidence: this.calculatePatternConfidence(pattern),
              metadata: {
                pattern: pattern.pattern,
                frequency: pattern.frequency,
                source: 'user_patterns'
              }
            });
            this.metrics.patternBasedSuggestions++;
          }
        }
      }
    }
    
    return suggestions;
  }

  async generateClusterBasedSuggestions(context) {
    const suggestions = [];
    
    if (!context.embedding) return suggestions;
    
    // Find similar memories in clusters
    const similar = await semanticClusterer.findSimilarInCluster(
      context.embedding,
      0.7
    );
    
    if (similar.length === 0) return suggestions;
    
    // Extract suggestions from similar memories
    const clusterId = similar[0].clusterId;
    if (clusterId) {
      const clusterMembers = await this.getClusterMembers(clusterId);
      
      // Find common actions in cluster
      const actionFrequency = new Map();
      for (const member of clusterMembers) {
        if (member.metadata?.action) {
          const action = member.metadata.action;
          actionFrequency.set(action, (actionFrequency.get(action) || 0) + 1);
        }
      }
      
      // Create suggestions from frequent actions
      for (const [action, frequency] of actionFrequency.entries()) {
        if (frequency >= 2) {
          suggestions.push({
            type: 'cluster',
            action,
            reason: `Related to ${similar.length} similar contexts`,
            confidence: this.calculateClusterConfidence(frequency, clusterMembers.length),
            metadata: {
              clusterId,
              similarityScore: similar[0].similarity,
              clusterSize: clusterMembers.length
            }
          });
        }
      }
    }
    
    return suggestions;
  }

  async generateContextualSuggestions(context, recentEpisodes) {
    const suggestions = [];
    
    // Analyze current context
    const contextFeatures = this.extractContextFeatures(context);
    
    // Time-based suggestions
    const hour = new Date().getHours();
    if (hour >= 9 && hour <= 11) {
      suggestions.push({
        type: 'contextual',
        action: 'review_morning_tasks',
        reason: 'Morning routine optimization',
        confidence: 0.7,
        metadata: { trigger: 'time_of_day' }
      });
    }
    
    // Error recovery suggestions
    const recentError = recentEpisodes.find(e => e.event?.type === 'error');
    if (recentError) {
      suggestions.push({
        type: 'contextual',
        action: 'debug_assistance',
        reason: 'Recent error detected',
        confidence: 0.85,
        metadata: { 
          errorType: recentError.event.message,
          trigger: 'error_detection'
        }
      });
    }
    
    // Project-specific suggestions
    if (context.projectId) {
      const projectContext = await this.getProjectContext(context.projectId);
      if (projectContext?.stack) {
        for (const tech of projectContext.stack) {
          suggestions.push({
            type: 'contextual',
            action: `${tech}_best_practices`,
            reason: `Project uses ${tech}`,
            confidence: 0.65,
            metadata: { 
              projectId: context.projectId,
              technology: tech
            }
          });
        }
      }
    }
    
    this.metrics.contextBasedSuggestions += suggestions.length;
    
    return suggestions;
  }

  async generateHistoricalSuggestions(context, userContext) {
    const suggestions = [];
    
    // Get user's frequent actions
    if (userContext.facts) {
      const frequentActions = userContext.facts
        .filter(f => f.confidence > 0.7)
        .map(f => this.extractActionFromFact(f.content))
        .filter(Boolean);
      
      for (const action of frequentActions.slice(0, 3)) {
        suggestions.push({
          type: 'historical',
          action,
          reason: 'Frequently performed action',
          confidence: 0.75,
          metadata: { source: 'user_history' }
        });
      }
    }
    
    return suggestions;
  }

  extractNextAction(pattern, currentSequence) {
    // Extract the next action from a pattern
    const remaining = pattern.substring(currentSequence.length);
    const match = remaining.match(/^-?>([^->]+)/);
    return match ? match[1] : null;
  }

  extractActionFromFact(fact) {
    // Simple extraction - in production, use NLP
    const match = fact.match(/implemented:\s*(.+)|created:\s*(.+)|fixed:\s*(.+)/i);
    if (match) {
      return match[1] || match[2] || match[3];
    }
    return null;
  }

  calculatePatternConfidence(pattern) {
    // Base confidence on frequency and recency
    const baseConfidence = Math.min(pattern.frequency / 10, 0.5);
    const recencyBoost = pattern.lastSeen 
      ? Math.exp(-(Date.now() - pattern.lastSeen) / (7 * 24 * 60 * 60 * 1000))
      : 0;
    
    return Math.min(baseConfidence + recencyBoost * 0.5, 1.0);
  }

  calculateClusterConfidence(frequency, clusterSize) {
    // Confidence based on frequency within cluster
    const ratio = frequency / clusterSize;
    return Math.min(0.5 + ratio * 0.5, 1.0);
  }

  scoreSuggestions(suggestions, context) {
    const scored = [];
    const seen = new Set();
    
    for (const suggestion of suggestions) {
      const key = `${suggestion.type}:${suggestion.action}`;
      
      if (!seen.has(key)) {
        seen.add(key);
        
        // Apply scoring factors
        let score = suggestion.confidence;
        
        // Boost for pattern-based suggestions
        if (suggestion.type === 'pattern') {
          score *= 1.2;
        }
        
        // Boost for recent context match
        if (suggestion.metadata?.trigger === 'error_detection') {
          score *= 1.3;
        }
        
        // Penalty for generic suggestions
        if (suggestion.action.includes('best_practices')) {
          score *= 0.8;
        }
        
        scored.push({
          ...suggestion,
          confidence: Math.min(score, 1.0),
          id: `suggestion_${Date.now()}_${Math.random().toString(36).substr(2, 9)}`
        });
      }
    }
    
    return scored;
  }

  async trackAcceptance(suggestionId, accepted) {
    const suggestion = this.suggestions.get(suggestionId);
    
    if (!suggestion) {
      logger.warn('Suggestion not found for tracking', { suggestionId });
      return;
    }
    
    if (accepted) {
      this.metrics.acceptedSuggestions++;
      
      // Boost confidence for similar suggestions
      if (suggestion.type === 'pattern' && suggestion.metadata?.pattern) {
        await this.boostPatternConfidence(suggestion.metadata.pattern);
      }
    } else {
      this.metrics.rejectedSuggestions++;
      
      // Reduce confidence for similar suggestions
      if (suggestion.type === 'pattern' && suggestion.metadata?.pattern) {
        await this.reducePatternConfidence(suggestion.metadata.pattern);
      }
    }
    
    // Store feedback for learning
    await this.storeFeedback(suggestion, accepted);
    
    logger.info('Suggestion feedback tracked', {
      suggestionId,
      accepted,
      type: suggestion.type
    });
  }

  async getUserContext(userId) {
    if (!userId) return { patterns: [], facts: [] };
    
    try {
      const bootstrapped = await persistentMemory.bootstrapSession(userId);
      return {
        patterns: bootstrapped.patterns || [],
        facts: bootstrapped.facts || [],
        preferences: bootstrapped.preferences || {}
      };
    } catch (error) {
      logger.error('Failed to get user context', { error: error.message });
      return { patterns: [], facts: [] };
    }
  }

  async getProjectContext(projectId) {
    // In production, retrieve from persistent memory
    return {
      stack: ['node', 'react'],
      patterns: []
    };
  }

  async getClusterMembers(clusterId) {
    // Get all memories in a cluster
    const allMemories = Array.from(semanticClusterer.memories.values());
    return allMemories.filter(m => m.clusterId === clusterId);
  }

  extractContextFeatures(context) {
    return {
      hasError: context.error !== undefined,
      hasCode: context.code !== undefined,
      hasQuery: context.query !== undefined,
      timeOfDay: new Date().getHours(),
      dayOfWeek: new Date().getDay(),
      projectId: context.projectId,
      userId: context.userId
    };
  }

  getCacheKey(context) {
    const features = this.extractContextFeatures(context);
    return JSON.stringify(features);
  }

  async loadUserPatterns() {
    // Load common patterns on initialization
    logger.debug('Loading user patterns for suggestion engine');
  }

  async boostPatternConfidence(pattern) {
    // Increase confidence for accepted patterns
    logger.debug('Boosting pattern confidence', { pattern });
  }

  async reducePatternConfidence(pattern) {
    // Decrease confidence for rejected patterns
    logger.debug('Reducing pattern confidence', { pattern });
  }

  async storeFeedback(suggestion, accepted) {
    // Store feedback for future learning
    const feedback = {
      suggestion,
      accepted,
      timestamp: Date.now(),
      context: suggestion.metadata
    };
    
    // In production, persist to database
    logger.debug('Stored suggestion feedback', { 
      type: suggestion.type,
      accepted 
    });
  }

  updateMetrics(suggestions, generationTime) {
    this.metrics.totalSuggestions += suggestions.length;
    
    // Update average generation time
    const prevAvg = this.metrics.avgGenerationTime;
    const totalGens = this.metrics.totalSuggestions;
    this.metrics.avgGenerationTime = 
      (prevAvg * (totalGens - suggestions.length) + generationTime) / totalGens;
  }

  async getMetrics() {
    const acceptanceRate = this.metrics.totalSuggestions > 0
      ? this.metrics.acceptedSuggestions / this.metrics.totalSuggestions
      : 0;
    
    return {
      ...this.metrics,
      acceptanceRate,
      cacheHitRate: this.suggestionCache.size / Math.max(this.metrics.totalSuggestions, 1)
    };
  }

  clearCache() {
    this.suggestionCache.clear();
    logger.debug('Suggestion cache cleared');
  }
}

export default new SuggestionEngine();