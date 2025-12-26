import winston from 'winston';
import { performance } from 'perf_hooks';
import { config } from '../../config/rag-config.js';
import learningFeedback from '../proactive/learning-feedback.js';
import suggestionEngine from '../proactive/suggestion-engine.js';

const logger = winston.createLogger({
  level: config.logging.level,
  format: winston.format.json(),
  transports: [
    new winston.transports.Console(),
    new winston.transports.File({ filename: config.logging.file })
  ]
});

class ModelTuner {
  constructor() {
    this.confidenceThresholds = new Map();
    this.patternWeights = new Map();
    this.rankingModels = new Map();
    this.predictionModels = new Map();
    this.tuningHistory = [];
    this.learningRate = 0.01;
    this.decayFactor = 0.99;
    this.minConfidence = 0.3;
    this.maxConfidence = 0.95;
    this.metrics = {
      totalAdjustments: 0,
      thresholdUpdates: 0,
      weightUpdates: 0,
      modelOptimizations: 0,
      avgImprovement: 0
    };
  }

  async initialize() {
    logger.info('Initializing model tuner...');
    await this.loadCurrentModels();
    this.startAdaptiveTuning();
    logger.info('Model tuner initialized');
  }

  async adjustConfidenceThreshold(type, performance) {
    const startTime = performance.now();
    
    // Get current threshold
    let threshold = this.confidenceThresholds.get(type) || {
      value: 0.6,
      history: [],
      lastUpdate: Date.now()
    };
    
    // Calculate adjustment based on performance
    const adjustment = this.calculateThresholdAdjustment(performance);
    
    // Apply adjustment with learning rate
    const oldValue = threshold.value;
    threshold.value += adjustment * this.learningRate;
    
    // Clamp to valid range
    threshold.value = Math.max(this.minConfidence, Math.min(this.maxConfidence, threshold.value));
    
    // Update history
    threshold.history.push({
      timestamp: Date.now(),
      oldValue,
      newValue: threshold.value,
      performance,
      adjustment
    });
    
    // Keep only recent history
    if (threshold.history.length > 100) {
      threshold.history.shift();
    }
    
    threshold.lastUpdate = Date.now();
    
    // Store updated threshold
    this.confidenceThresholds.set(type, threshold);
    this.metrics.thresholdUpdates++;
    
    // Apply to suggestion engine
    await this.applyThresholdUpdate(type, threshold.value);
    
    const processingTime = performance.now() - startTime;
    
    logger.debug('Adjusted confidence threshold', {
      type,
      oldValue: oldValue.toFixed(3),
      newValue: threshold.value.toFixed(3),
      adjustment: adjustment.toFixed(3),
      time: `${processingTime.toFixed(2)}ms`
    });
    
    return threshold.value;
  }

  calculateThresholdAdjustment(performance) {
    // Higher success rate -> lower threshold (more suggestions)
    // Lower success rate -> higher threshold (fewer, better suggestions)
    
    const targetSuccessRate = 0.7;
    const error = targetSuccessRate - performance.successRate;
    
    // Proportional adjustment
    let adjustment = error * 0.5;
    
    // Consider acceptance rate
    if (performance.acceptanceRate !== undefined) {
      const acceptanceError = 0.6 - performance.acceptanceRate;
      adjustment += acceptanceError * 0.3;
    }
    
    // Consider false positive rate
    if (performance.falsePositiveRate !== undefined) {
      adjustment += performance.falsePositiveRate * 0.2;
    }
    
    return adjustment;
  }

  async updatePatternWeights(patterns, feedback) {
    const updates = [];
    
    for (const pattern of patterns) {
      const key = pattern.id || pattern.pattern;
      
      // Get current weight
      let weight = this.patternWeights.get(key) || {
        value: 1.0,
        occurrences: 0,
        successCount: 0,
        lastUpdate: Date.now()
      };
      
      // Update based on feedback
      weight.occurrences++;
      if (feedback.positive) {
        weight.successCount++;
      }
      
      // Calculate new weight
      const successRate = weight.successCount / weight.occurrences;
      const targetWeight = successRate * 1.5; // Boost successful patterns
      
      // Apply with decay
      weight.value = weight.value * this.decayFactor + targetWeight * (1 - this.decayFactor);
      
      // Clamp weights
      weight.value = Math.max(0.1, Math.min(2.0, weight.value));
      
      weight.lastUpdate = Date.now();
      
      // Store updated weight
      this.patternWeights.set(key, weight);
      
      updates.push({
        pattern: key,
        weight: weight.value,
        successRate
      });
    }
    
    this.metrics.weightUpdates += updates.length;
    
    logger.debug('Updated pattern weights', {
      count: updates.length,
      avgWeight: updates.reduce((sum, u) => sum + u.weight, 0) / updates.length
    });
    
    return updates;
  }

  async fineTuneRankings(suggestions, feedback) {
    const modelKey = this.getRankingModelKey(suggestions);
    
    // Get or create ranking model
    let model = this.rankingModels.get(modelKey) || {
      weights: {
        confidence: 1.0,
        recency: 0.8,
        frequency: 0.6,
        userPreference: 1.2,
        contextMatch: 0.9
      },
      performance: [],
      lastUpdate: Date.now()
    };
    
    // Update weights based on feedback
    if (feedback.accepted) {
      // Boost weights of features that contributed to accepted suggestion
      const topSuggestion = suggestions[0];
      
      if (topSuggestion.confidence > 0.8) {
        model.weights.confidence *= 1.05;
      }
      
      if (topSuggestion.metadata?.recency) {
        model.weights.recency *= 1.03;
      }
    } else {
      // Reduce weights if rejected
      model.weights.confidence *= 0.98;
    }
    
    // Normalize weights
    const totalWeight = Object.values(model.weights).reduce((a, b) => a + b, 0);
    for (const key in model.weights) {
      model.weights[key] /= totalWeight;
    }
    
    // Track performance
    model.performance.push({
      timestamp: Date.now(),
      accepted: feedback.accepted,
      weights: { ...model.weights }
    });
    
    // Keep limited history
    if (model.performance.length > 50) {
      model.performance.shift();
    }
    
    model.lastUpdate = Date.now();
    
    // Store updated model
    this.rankingModels.set(modelKey, model);
    
    // Apply new ranking
    const reranked = await this.applyRanking(suggestions, model.weights);
    
    logger.debug('Fine-tuned ranking model', {
      modelKey,
      weights: model.weights
    });
    
    return reranked;
  }

  async optimizePredictionModel(type, performance) {
    const modelKey = `prediction_${type}`;
    
    // Get or create prediction model
    let model = this.predictionModels.get(modelKey) || {
      parameters: {
        lookbackWindow: 5,
        minConfidence: 0.6,
        maxPredictions: 3,
        timeDecay: 0.9
      },
      performance: [],
      bestParameters: null,
      lastOptimization: Date.now()
    };
    
    // Track current performance
    model.performance.push({
      timestamp: Date.now(),
      accuracy: performance.accuracy,
      parameters: { ...model.parameters }
    });
    
    // Optimize if enough data
    if (model.performance.length >= 10) {
      const optimized = this.optimizeParameters(model);
      
      if (optimized.improvement > 0.05) {
        model.parameters = optimized.parameters;
        model.bestParameters = optimized.parameters;
        
        logger.info('Optimized prediction model', {
          type,
          improvement: `${(optimized.improvement * 100).toFixed(1)}%`
        });
      }
    }
    
    model.lastOptimization = Date.now();
    
    // Store updated model
    this.predictionModels.set(modelKey, model);
    this.metrics.modelOptimizations++;
    
    return model.parameters;
  }

  optimizeParameters(model) {
    const recent = model.performance.slice(-10);
    let bestParams = model.parameters;
    let bestAccuracy = recent[recent.length - 1].accuracy;
    
    // Try variations
    const variations = [
      { lookbackWindow: model.parameters.lookbackWindow + 1 },
      { lookbackWindow: Math.max(3, model.parameters.lookbackWindow - 1) },
      { minConfidence: model.parameters.minConfidence + 0.05 },
      { minConfidence: Math.max(0.4, model.parameters.minConfidence - 0.05) },
      { maxPredictions: model.parameters.maxPredictions + 1 },
      { maxPredictions: Math.max(1, model.parameters.maxPredictions - 1) }
    ];
    
    for (const variation of variations) {
      const params = { ...model.parameters, ...variation };
      const estimatedAccuracy = this.estimateAccuracy(params, recent);
      
      if (estimatedAccuracy > bestAccuracy) {
        bestAccuracy = estimatedAccuracy;
        bestParams = params;
      }
    }
    
    return {
      parameters: bestParams,
      improvement: bestAccuracy - recent[recent.length - 1].accuracy
    };
  }

  estimateAccuracy(params, performanceHistory) {
    // Simple estimation based on parameter correlation
    let score = 0.5; // Base score
    
    // Larger lookback generally helps
    score += (params.lookbackWindow / 10) * 0.1;
    
    // Moderate confidence is best
    const confDiff = Math.abs(params.minConfidence - 0.7);
    score -= confDiff * 0.2;
    
    // More predictions can help but not too many
    if (params.maxPredictions <= 5) {
      score += (params.maxPredictions / 10) * 0.1;
    }
    
    return Math.min(Math.max(score, 0), 1);
  }

  async applyThresholdUpdate(type, threshold) {
    // Apply to learning feedback system
    try {
      if (learningFeedback.thresholds) {
        if (type === 'confidence') {
          learningFeedback.thresholds.confidence = threshold;
        } else if (type === 'acceptance') {
          learningFeedback.thresholds.acceptance = threshold;
        }
      }
      
      logger.debug('Applied threshold update to learning feedback', {
        type,
        threshold
      });
    } catch (error) {
      logger.error('Failed to apply threshold update', { error: error.message });
    }
  }

  async applyRanking(suggestions, weights) {
    return suggestions.map(suggestion => {
      let score = 0;
      
      score += (suggestion.confidence || 0) * weights.confidence;
      score += (suggestion.metadata?.recency || 0) * weights.recency;
      score += (suggestion.metadata?.frequency || 0) * weights.frequency;
      score += (suggestion.metadata?.userPreference || 0) * weights.userPreference;
      score += (suggestion.metadata?.contextMatch || 0) * weights.contextMatch;
      
      return {
        ...suggestion,
        rankingScore: score
      };
    }).sort((a, b) => b.rankingScore - a.rankingScore);
  }

  getRankingModelKey(suggestions) {
    // Create key based on suggestion types
    const types = suggestions.map(s => s.type).slice(0, 3).sort().join(':');
    return `ranking_${types}`;
  }

  async autoTune(performanceData) {
    const improvements = [];
    
    // Auto-tune confidence thresholds
    for (const [type, data] of Object.entries(performanceData.byType || {})) {
      if (data.total >= 10) {
        const adjustment = await this.adjustConfidenceThreshold(type, data);
        improvements.push({
          type: 'threshold',
          target: type,
          adjustment
        });
      }
    }
    
    // Auto-tune pattern weights
    if (performanceData.patterns) {
      const updates = await this.updatePatternWeights(
        performanceData.patterns,
        { positive: performanceData.overallSuccess > 0.6 }
      );
      
      improvements.push({
        type: 'weights',
        count: updates.length
      });
    }
    
    // Track improvement
    if (improvements.length > 0) {
      this.tuningHistory.push({
        timestamp: Date.now(),
        improvements,
        performance: performanceData.overallSuccess
      });
      
      // Calculate average improvement
      if (this.tuningHistory.length >= 2) {
        const recent = this.tuningHistory.slice(-10);
        const improvement = recent[recent.length - 1].performance - recent[0].performance;
        this.metrics.avgImprovement = improvement;
      }
    }
    
    this.metrics.totalAdjustments += improvements.length;
    
    logger.info('Auto-tuning completed', {
      improvements: improvements.length,
      avgImprovement: `${(this.metrics.avgImprovement * 100).toFixed(1)}%`
    });
    
    return improvements;
  }

  async loadCurrentModels() {
    // Load current model states
    try {
      // In production, would load from persistent storage
      logger.debug('Loaded current model states');
    } catch (error) {
      logger.error('Failed to load models', { error: error.message });
    }
  }

  startAdaptiveTuning() {
    // Periodic adaptive tuning
    setInterval(async () => {
      await this.performAdaptiveTuning();
    }, 60 * 60 * 1000); // Every hour
  }

  async performAdaptiveTuning() {
    try {
      // Decay old weights
      for (const [key, weight] of this.patternWeights.entries()) {
        if (Date.now() - weight.lastUpdate > 24 * 60 * 60 * 1000) {
          weight.value *= this.decayFactor;
          this.patternWeights.set(key, weight);
        }
      }
      
      // Clean old models
      this.cleanOldModels();
      
      logger.debug('Performed adaptive tuning');
    } catch (error) {
      logger.error('Adaptive tuning failed', { error: error.message });
    }
  }

  cleanOldModels() {
    const cutoff = Date.now() - 7 * 24 * 60 * 60 * 1000; // 7 days
    
    // Clean ranking models
    for (const [key, model] of this.rankingModels.entries()) {
      if (model.lastUpdate < cutoff) {
        this.rankingModels.delete(key);
      }
    }
    
    // Clean prediction models
    for (const [key, model] of this.predictionModels.entries()) {
      if (model.lastOptimization < cutoff) {
        this.predictionModels.delete(key);
      }
    }
  }

  async getModelStats() {
    const stats = {
      thresholds: {},
      weights: {},
      rankings: {},
      predictions: {}
    };
    
    // Threshold stats
    for (const [type, threshold] of this.confidenceThresholds.entries()) {
      stats.thresholds[type] = {
        value: threshold.value,
        recentChanges: threshold.history.slice(-5).map(h => h.adjustment)
      };
    }
    
    // Weight stats
    const weights = Array.from(this.patternWeights.values());
    if (weights.length > 0) {
      stats.weights = {
        count: weights.length,
        avgWeight: weights.reduce((sum, w) => sum + w.value, 0) / weights.length,
        highPerformers: weights.filter(w => w.value > 1.5).length
      };
    }
    
    // Model counts
    stats.rankings.count = this.rankingModels.size;
    stats.predictions.count = this.predictionModels.size;
    
    return stats;
  }

  async getMetrics() {
    const stats = await this.getModelStats();
    
    return {
      ...this.metrics,
      activeThresholds: this.confidenceThresholds.size,
      activeWeights: this.patternWeights.size,
      rankingModels: this.rankingModels.size,
      predictionModels: this.predictionModels.size,
      modelStats: stats
    };
  }
}

export default new ModelTuner();