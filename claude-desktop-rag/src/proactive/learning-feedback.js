import winston from 'winston';
import { v4 as uuidv4 } from 'uuid';
import { config } from '../../config/rag-config.js';
import persistentMemory from '../memory/advanced/persistent-memory.js';

const logger = winston.createLogger({
  level: config.logging.level,
  format: winston.format.json(),
  transports: [
    new winston.transports.Console(),
    new winston.transports.File({ filename: config.logging.file })
  ]
});

class LearningFeedback {
  constructor() {
    this.feedbackHistory = new Map();
    this.confidenceAdjustments = new Map();
    this.modelImprovements = new Map();
    this.thresholds = {
      confidence: 0.6,
      acceptance: 0.5,
      learning: 0.1
    };
    this.learningRate = 0.1;
    this.decayFactor = 0.95;
    this.metrics = {
      totalFeedback: 0,
      acceptedSuggestions: 0,
      rejectedSuggestions: 0,
      modelUpdates: 0,
      confidenceImprovement: 0,
      avgAcceptanceRate: 0
    };
  }

  async initialize() {
    logger.info('Initializing learning feedback system...');
    await this.loadHistoricalFeedback();
    this.startPeriodicAnalysis();
    logger.info('Learning feedback system initialized');
  }

  async trackSuggestion(suggestion, accepted, context = {}) {
    const feedbackId = uuidv4();
    
    const feedback = {
      id: feedbackId,
      suggestionId: suggestion.id,
      type: suggestion.type,
      action: suggestion.action,
      confidence: suggestion.confidence,
      accepted,
      context,
      timestamp: Date.now(),
      userId: context.userId,
      projectId: context.projectId
    };
    
    // Store feedback
    this.feedbackHistory.set(feedbackId, feedback);
    
    // Update metrics
    this.metrics.totalFeedback++;
    if (accepted) {
      this.metrics.acceptedSuggestions++;
    } else {
      this.metrics.rejectedSuggestions++;
    }
    
    // Adjust confidence
    await this.adjustConfidence(suggestion, accepted);
    
    // Update prediction model
    await this.updatePredictionModel(feedback);
    
    // Learn from pattern
    if (suggestion.metadata?.pattern) {
      await this.learnFromPattern(suggestion.metadata.pattern, accepted);
    }
    
    // Store for persistent learning
    await this.persistFeedback(feedback);
    
    logger.debug('Feedback tracked', {
      suggestionId: suggestion.id,
      accepted,
      type: suggestion.type
    });
    
    return feedbackId;
  }

  async adjustConfidence(suggestion, accepted) {
    const key = `${suggestion.type}:${suggestion.action}`;
    
    // Get current adjustment
    let adjustment = this.confidenceAdjustments.get(key) || {
      positive: 0,
      negative: 0,
      total: 0,
      currentMultiplier: 1.0
    };
    
    // Update counts
    adjustment.total++;
    if (accepted) {
      adjustment.positive++;
    } else {
      adjustment.negative++;
    }
    
    // Calculate new multiplier
    const acceptanceRate = adjustment.positive / adjustment.total;
    const targetRate = 0.7; // Target 70% acceptance
    
    // Adjust multiplier based on acceptance rate
    if (acceptanceRate < targetRate) {
      // Reduce confidence if rejection rate is high
      adjustment.currentMultiplier *= (1 - this.learningRate);
    } else if (acceptanceRate > targetRate + 0.1) {
      // Increase confidence if acceptance rate is very high
      adjustment.currentMultiplier *= (1 + this.learningRate * 0.5);
    }
    
    // Clamp multiplier
    adjustment.currentMultiplier = Math.max(0.5, Math.min(1.5, adjustment.currentMultiplier));
    
    this.confidenceAdjustments.set(key, adjustment);
    
    logger.debug('Confidence adjusted', {
      key,
      acceptanceRate: acceptanceRate.toFixed(2),
      multiplier: adjustment.currentMultiplier.toFixed(2)
    });
  }

  async updatePredictionModel(feedback) {
    const modelKey = feedback.userId || 'global';
    
    let model = this.modelImprovements.get(modelKey) || {
      patterns: new Map(),
      contexts: new Map(),
      improvements: []
    };
    
    // Update pattern statistics
    if (feedback.type === 'pattern') {
      const patternStats = model.patterns.get(feedback.action) || {
        occurrences: 0,
        accepted: 0
      };
      
      patternStats.occurrences++;
      if (feedback.accepted) {
        patternStats.accepted++;
      }
      
      model.patterns.set(feedback.action, patternStats);
    }
    
    // Update context effectiveness
    const contextKey = this.getContextKey(feedback.context);
    const contextStats = model.contexts.get(contextKey) || {
      suggestions: 0,
      accepted: 0
    };
    
    contextStats.suggestions++;
    if (feedback.accepted) {
      contextStats.accepted++;
    }
    
    model.contexts.set(contextKey, contextStats);
    
    // Identify improvements
    if (model.patterns.size >= 10 && model.improvements.length === 0) {
      model.improvements = this.identifyModelImprovements(model);
    }
    
    this.modelImprovements.set(modelKey, model);
    this.metrics.modelUpdates++;
  }

  identifyModelImprovements(model) {
    const improvements = [];
    
    // Find poorly performing patterns
    for (const [action, stats] of model.patterns.entries()) {
      const acceptanceRate = stats.accepted / stats.occurrences;
      
      if (acceptanceRate < 0.3 && stats.occurrences >= 5) {
        improvements.push({
          type: 'remove_pattern',
          action,
          reason: 'Low acceptance rate',
          acceptanceRate
        });
      } else if (acceptanceRate > 0.9 && stats.occurrences >= 10) {
        improvements.push({
          type: 'boost_pattern',
          action,
          reason: 'High acceptance rate',
          acceptanceRate
        });
      }
    }
    
    // Find effective contexts
    for (const [context, stats] of model.contexts.entries()) {
      const effectiveness = stats.accepted / stats.suggestions;
      
      if (effectiveness > 0.8 && stats.suggestions >= 5) {
        improvements.push({
          type: 'prioritize_context',
          context,
          effectiveness
        });
      }
    }
    
    return improvements;
  }

  async learnFromPattern(pattern, accepted) {
    // Specific learning for pattern-based suggestions
    const patternKey = typeof pattern === 'string' ? pattern : pattern.sequence;
    
    // Update pattern confidence
    const confidence = await this.getPatternConfidence(patternKey);
    const newConfidence = accepted
      ? confidence + this.learningRate * (1 - confidence)
      : confidence * this.decayFactor;
    
    await this.setPatternConfidence(patternKey, newConfidence);
    
    logger.debug('Pattern learning applied', {
      pattern: patternKey,
      accepted,
      newConfidence: newConfidence.toFixed(2)
    });
  }

  async improveThresholds() {
    // Analyze feedback to improve thresholds
    const recentFeedback = Array.from(this.feedbackHistory.values())
      .filter(f => Date.now() - f.timestamp < 24 * 60 * 60 * 1000); // Last 24 hours
    
    if (recentFeedback.length < 20) {
      return; // Not enough data
    }
    
    // Analyze acceptance by confidence level
    const confidenceBuckets = new Map();
    
    for (const feedback of recentFeedback) {
      const bucket = Math.floor(feedback.confidence * 10) / 10;
      
      if (!confidenceBuckets.has(bucket)) {
        confidenceBuckets.set(bucket, { total: 0, accepted: 0 });
      }
      
      const stats = confidenceBuckets.get(bucket);
      stats.total++;
      if (feedback.accepted) {
        stats.accepted++;
      }
    }
    
    // Find optimal confidence threshold
    let optimalThreshold = this.thresholds.confidence;
    let maxEffectiveness = 0;
    
    for (const [confidence, stats] of confidenceBuckets.entries()) {
      if (stats.total >= 5) {
        const acceptanceRate = stats.accepted / stats.total;
        const effectiveness = acceptanceRate * stats.total / recentFeedback.length;
        
        if (effectiveness > maxEffectiveness && acceptanceRate >= 0.6) {
          maxEffectiveness = effectiveness;
          optimalThreshold = confidence;
        }
      }
    }
    
    // Update threshold with smoothing
    const oldThreshold = this.thresholds.confidence;
    this.thresholds.confidence = 
      oldThreshold * 0.9 + optimalThreshold * 0.1;
    
    if (Math.abs(this.thresholds.confidence - oldThreshold) > 0.05) {
      logger.info('Confidence threshold adjusted', {
        old: oldThreshold.toFixed(2),
        new: this.thresholds.confidence.toFixed(2)
      });
    }
    
    // Calculate overall improvement
    const currentAcceptance = recentFeedback.filter(f => f.accepted).length / recentFeedback.length;
    this.metrics.avgAcceptanceRate = 
      this.metrics.avgAcceptanceRate * 0.9 + currentAcceptance * 0.1;
    
    if (currentAcceptance > this.metrics.avgAcceptanceRate) {
      this.metrics.confidenceImprovement++;
    }
  }

  async analyzeFeedbackPatterns() {
    const analysis = {
      byType: new Map(),
      byTime: new Map(),
      byUser: new Map(),
      trends: []
    };
    
    const allFeedback = Array.from(this.feedbackHistory.values());
    
    // Analyze by suggestion type
    for (const feedback of allFeedback) {
      const typeStats = analysis.byType.get(feedback.type) || {
        total: 0,
        accepted: 0
      };
      
      typeStats.total++;
      if (feedback.accepted) {
        typeStats.accepted++;
      }
      
      analysis.byType.set(feedback.type, typeStats);
    }
    
    // Analyze by time of day
    for (const feedback of allFeedback) {
      const hour = new Date(feedback.timestamp).getHours();
      const timeStats = analysis.byTime.get(hour) || {
        total: 0,
        accepted: 0
      };
      
      timeStats.total++;
      if (feedback.accepted) {
        timeStats.accepted++;
      }
      
      analysis.byTime.set(hour, timeStats);
    }
    
    // Identify trends
    const recentFeedback = allFeedback
      .filter(f => Date.now() - f.timestamp < 7 * 24 * 60 * 60 * 1000)
      .sort((a, b) => a.timestamp - b.timestamp);
    
    if (recentFeedback.length >= 20) {
      const firstHalf = recentFeedback.slice(0, Math.floor(recentFeedback.length / 2));
      const secondHalf = recentFeedback.slice(Math.floor(recentFeedback.length / 2));
      
      const firstAcceptance = firstHalf.filter(f => f.accepted).length / firstHalf.length;
      const secondAcceptance = secondHalf.filter(f => f.accepted).length / secondHalf.length;
      
      if (secondAcceptance > firstAcceptance + 0.1) {
        analysis.trends.push('improving_acceptance');
      } else if (secondAcceptance < firstAcceptance - 0.1) {
        analysis.trends.push('declining_acceptance');
      }
    }
    
    return analysis;
  }

  async getAdjustedConfidence(type, action, baseConfidence) {
    const key = `${type}:${action}`;
    const adjustment = this.confidenceAdjustments.get(key);
    
    if (!adjustment) {
      return baseConfidence;
    }
    
    return Math.max(0, Math.min(1, baseConfidence * adjustment.currentMultiplier));
  }

  async persistFeedback(feedback) {
    try {
      // Store as a fact in persistent memory
      await persistentMemory.consolidateSession(feedback.userId || 'system', {
        interactions: [{
          type: 'feedback',
          content: `${feedback.type}:${feedback.action}`,
          accepted: feedback.accepted
        }],
        facts: feedback.accepted 
          ? [`User accepts ${feedback.type} suggestions for ${feedback.action}`]
          : [`User rejects ${feedback.type} suggestions for ${feedback.action}`]
      });
    } catch (error) {
      logger.error('Failed to persist feedback', { error: error.message });
    }
  }

  async loadHistoricalFeedback() {
    // In production, load from persistent storage
    logger.debug('Loading historical feedback data');
  }

  getContextKey(context) {
    // Create a key from context features
    const features = [];
    
    if (context.projectId) features.push(`project:${context.projectId}`);
    if (context.error) features.push('has_error');
    if (context.codeFile) features.push('has_code');
    
    return features.join('|') || 'default';
  }

  async getPatternConfidence(pattern) {
    // Retrieve stored pattern confidence
    const key = `pattern:${pattern}`;
    const adjustment = this.confidenceAdjustments.get(key);
    
    return adjustment ? adjustment.currentMultiplier : 1.0;
  }

  async setPatternConfidence(pattern, confidence) {
    const key = `pattern:${pattern}`;
    const adjustment = this.confidenceAdjustments.get(key) || {
      positive: 0,
      negative: 0,
      total: 0,
      currentMultiplier: 1.0
    };
    
    adjustment.currentMultiplier = confidence;
    this.confidenceAdjustments.set(key, adjustment);
  }

  startPeriodicAnalysis() {
    // Run analysis every hour
    setInterval(async () => {
      try {
        await this.improveThresholds();
        
        const analysis = await this.analyzeFeedbackPatterns();
        
        logger.info('Periodic feedback analysis completed', {
          trends: analysis.trends,
          avgAcceptance: this.metrics.avgAcceptanceRate.toFixed(2)
        });
        
        // Clean old feedback
        this.cleanOldFeedback();
      } catch (error) {
        logger.error('Periodic analysis failed', { error: error.message });
      }
    }, 60 * 60 * 1000);
  }

  cleanOldFeedback() {
    const cutoff = Date.now() - 30 * 24 * 60 * 60 * 1000; // 30 days
    let cleaned = 0;
    
    for (const [id, feedback] of this.feedbackHistory.entries()) {
      if (feedback.timestamp < cutoff) {
        this.feedbackHistory.delete(id);
        cleaned++;
      }
    }
    
    if (cleaned > 0) {
      logger.debug(`Cleaned ${cleaned} old feedback entries`);
    }
  }

  async getMetrics() {
    const acceptanceRate = this.metrics.totalFeedback > 0
      ? this.metrics.acceptedSuggestions / this.metrics.totalFeedback
      : 0;
    
    const analysis = await this.analyzeFeedbackPatterns();
    
    return {
      ...this.metrics,
      acceptanceRate,
      currentThreshold: this.thresholds.confidence,
      adjustedConfidences: this.confidenceAdjustments.size,
      modelImprovements: Array.from(this.modelImprovements.values())
        .reduce((sum, m) => sum + m.improvements.length, 0),
      trends: analysis.trends
    };
  }

  async reset() {
    this.feedbackHistory.clear();
    this.confidenceAdjustments.clear();
    this.modelImprovements.clear();
    
    this.metrics = {
      totalFeedback: 0,
      acceptedSuggestions: 0,
      rejectedSuggestions: 0,
      modelUpdates: 0,
      confidenceImprovement: 0,
      avgAcceptanceRate: 0
    };
    
    logger.info('Learning feedback system reset');
  }
}

export default new LearningFeedback();