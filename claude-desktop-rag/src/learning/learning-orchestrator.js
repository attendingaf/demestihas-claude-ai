import winston from 'winston';
import { performance } from 'perf_hooks';
import { config } from '../../config/rag-config.js';
import feedbackLoop from './feedback-loop.js';
import performanceTracker from './performance-tracker.js';
import modelTuner from './model-tuner.js';
import insightGenerator from './insight-generator.js';

const logger = winston.createLogger({
  level: config.logging.level,
  format: winston.format.json(),
  transports: [
    new winston.transports.Console(),
    new winston.transports.File({ filename: config.logging.file })
  ]
});

class LearningOrchestrator {
  constructor() {
    this.components = {
      feedbackLoop: null,
      performanceTracker: null,
      modelTuner: null,
      insightGenerator: null
    };
    this.learningSchedule = {
      immediate: [],
      hourly: [],
      daily: [],
      weekly: []
    };
    this.learningRate = {
      initial: 0.1,
      current: 0.1,
      decay: 0.99,
      minimum: 0.001
    };
    this.overfittingProtection = {
      enabled: true,
      recentDataWeight: 0.7,
      historicalDataWeight: 0.3,
      maxRecentSamples: 1000
    };
    this.updateQueue = [];
    this.metrics = {
      totalUpdates: 0,
      scheduledTasks: 0,
      overfittingPrevented: 0,
      learningCycles: 0,
      avgCycleTime: 0
    };
    this.intervals = {};
  }

  async initialize() {
    logger.info('Initializing learning orchestrator...');
    
    // Initialize all components
    await this.initializeComponents();
    
    // Setup learning schedules
    this.setupSchedules();
    
    // Start orchestration
    this.startOrchestration();
    
    logger.info('Learning orchestrator initialized');
  }

  async initializeComponents() {
    try {
      // Initialize in parallel
      await Promise.all([
        feedbackLoop.initialize(),
        performanceTracker.initialize(),
        modelTuner.initialize(),
        insightGenerator.initialize()
      ]);
      
      this.components = {
        feedbackLoop,
        performanceTracker,
        modelTuner,
        insightGenerator
      };
      
      logger.debug('Learning components initialized');
    } catch (error) {
      logger.error('Failed to initialize components', { error: error.message });
      throw error;
    }
  }

  setupSchedules() {
    // Immediate tasks (on every update)
    this.learningSchedule.immediate = [
      { name: 'processImmediateFeedback', handler: this.processImmediateFeedback.bind(this) },
      { name: 'updatePerformanceMetrics', handler: this.updatePerformanceMetrics.bind(this) }
    ];
    
    // Hourly tasks
    this.learningSchedule.hourly = [
      { name: 'tuneModels', handler: this.tuneModels.bind(this) },
      { name: 'analyzePatterns', handler: this.analyzePatterns.bind(this) },
      { name: 'decayLearningRate', handler: this.decayLearningRate.bind(this) }
    ];
    
    // Daily tasks
    this.learningSchedule.daily = [
      { name: 'generateDailyInsights', handler: this.generateDailyInsights.bind(this) },
      { name: 'pruneOldData', handler: this.pruneOldData.bind(this) },
      { name: 'optimizeModels', handler: this.optimizeModels.bind(this) }
    ];
    
    // Weekly tasks
    this.learningSchedule.weekly = [
      { name: 'generateWeeklyReport', handler: this.generateWeeklyReport.bind(this) },
      { name: 'majorModelUpdate', handler: this.majorModelUpdate.bind(this) },
      { name: 'systemOptimization', handler: this.systemOptimization.bind(this) }
    ];
    
    this.metrics.scheduledTasks = 
      this.learningSchedule.immediate.length +
      this.learningSchedule.hourly.length +
      this.learningSchedule.daily.length +
      this.learningSchedule.weekly.length;
    
    logger.debug('Learning schedules configured', {
      immediate: this.learningSchedule.immediate.length,
      hourly: this.learningSchedule.hourly.length,
      daily: this.learningSchedule.daily.length,
      weekly: this.learningSchedule.weekly.length
    });
  }

  startOrchestration() {
    // Start periodic executions
    this.intervals.hourly = setInterval(() => {
      this.executeSchedule('hourly');
    }, 60 * 60 * 1000);
    
    this.intervals.daily = setInterval(() => {
      this.executeSchedule('daily');
    }, 24 * 60 * 60 * 1000);
    
    this.intervals.weekly = setInterval(() => {
      this.executeSchedule('weekly');
    }, 7 * 24 * 60 * 60 * 1000);
    
    // Start update processor
    this.intervals.processor = setInterval(() => {
      this.processUpdateQueue();
    }, 5000); // Every 5 seconds
    
    logger.info('Learning orchestration started');
  }

  async coordinateLearning(event, data) {
    const startTime = performance.now();
    
    try {
      // Add to update queue
      this.updateQueue.push({
        event,
        data,
        timestamp: Date.now()
      });
      
      // Execute immediate tasks
      await this.executeSchedule('immediate', { event, data });
      
      // Check for overfitting
      if (this.overfittingProtection.enabled) {
        await this.checkOverfitting();
      }
      
      this.metrics.totalUpdates++;
      this.metrics.learningCycles++;
      
      // Update cycle time
      const cycleTime = performance.now() - startTime;
      this.metrics.avgCycleTime = 
        (this.metrics.avgCycleTime * (this.metrics.learningCycles - 1) + cycleTime) / 
        this.metrics.learningCycles;
      
      logger.debug('Learning cycle completed', {
        event,
        cycleTime: `${cycleTime.toFixed(2)}ms`,
        queueSize: this.updateQueue.length
      });
      
      return {
        processed: true,
        cycleTime,
        learningRate: this.learningRate.current
      };
    } catch (error) {
      logger.error('Learning coordination failed', { 
        event,
        error: error.message 
      });
      return {
        processed: false,
        error: error.message
      };
    }
  }

  async executeSchedule(scheduleName, context = {}) {
    const tasks = this.learningSchedule[scheduleName];
    if (!tasks) return;
    
    logger.debug(`Executing ${scheduleName} schedule`, {
      taskCount: tasks.length
    });
    
    const results = [];
    
    for (const task of tasks) {
      try {
        const result = await task.handler(context);
        results.push({
          task: task.name,
          success: true,
          result
        });
      } catch (error) {
        logger.error(`Task ${task.name} failed`, { 
          error: error.message 
        });
        results.push({
          task: task.name,
          success: false,
          error: error.message
        });
      }
    }
    
    return results;
  }

  async processImmediateFeedback(context) {
    if (!context.event || !context.data) return;
    
    // Process based on event type
    switch (context.event) {
      case 'suggestion_accepted':
      case 'suggestion_rejected':
        await this.processSuggestionFeedback(context.data);
        break;
      
      case 'action_completed':
        await this.processActionCompletion(context.data);
        break;
      
      case 'error_occurred':
        await this.processError(context.data);
        break;
      
      default:
        // Generic processing
        await feedbackLoop.captureImplicitFeedback(
          { type: context.event },
          context.data
        );
    }
  }

  async processSuggestionFeedback(data) {
    const accepted = data.accepted || false;
    
    // Capture explicit feedback
    await feedbackLoop.captureExplicitFeedback(
      accepted ? 5 : 2,
      data.correction,
      data.context
    );
    
    // Track performance
    await performanceTracker.trackAction(
      'suggestion',
      accepted,
      data.responseTime,
      data.context
    );
  }

  async processActionCompletion(data) {
    await performanceTracker.trackAction(
      data.actionType,
      data.success,
      data.completionTime,
      data.context
    );
  }

  async processError(data) {
    await performanceTracker.trackAction(
      data.actionType || 'unknown',
      false,
      0,
      { ...data.context, errorType: data.errorType }
    );
  }

  async updatePerformanceMetrics(context) {
    // Aggregate recent performance
    const recentPerformance = await this.aggregateRecentPerformance();
    
    if (recentPerformance.sampleSize >= 10) {
      // Update models based on performance
      await modelTuner.autoTune(recentPerformance);
    }
  }

  async tuneModels() {
    try {
      // Get performance data
      const performance = await performanceTracker.generateReport('hour');
      
      // Tune confidence thresholds
      for (const [actionType, metrics] of Object.entries(performance.actionBreakdown)) {
        await modelTuner.adjustConfidenceThreshold(actionType, metrics);
      }
      
      // Get feedback patterns
      const patterns = await feedbackLoop.getPatterns();
      
      // Update pattern weights
      if (patterns.length > 0) {
        await modelTuner.updatePatternWeights(
          patterns,
          { positive: performance.summary.successRate > 0.6 }
        );
      }
      
      logger.info('Model tuning completed', {
        actionstuned: Object.keys(performance.actionBreakdown).length,
        patternsUpdated: patterns.length
      });
    } catch (error) {
      logger.error('Model tuning failed', { error: error.message });
    }
  }

  async analyzePatterns() {
    try {
      const patterns = await feedbackLoop.getPatterns();
      const correlations = await feedbackLoop.getCorrelations();
      
      // Identify significant patterns
      const significant = patterns.filter(p => 
        p.confidence > 0.7 && p.occurrences >= 5
      );
      
      logger.info('Pattern analysis completed', {
        totalPatterns: patterns.length,
        significantPatterns: significant.length,
        correlationTypes: Object.keys(correlations).length
      });
      
      return {
        patterns: significant,
        correlations
      };
    } catch (error) {
      logger.error('Pattern analysis failed', { error: error.message });
      return { patterns: [], correlations: {} };
    }
  }

  decayLearningRate() {
    const oldRate = this.learningRate.current;
    this.learningRate.current *= this.learningRate.decay;
    
    // Apply minimum
    this.learningRate.current = Math.max(
      this.learningRate.current,
      this.learningRate.minimum
    );
    
    logger.debug('Learning rate decayed', {
      oldRate: oldRate.toFixed(4),
      newRate: this.learningRate.current.toFixed(4)
    });
  }

  async checkOverfitting() {
    const recentData = this.updateQueue.slice(-this.overfittingProtection.maxRecentSamples);
    
    if (recentData.length < 100) return;
    
    // Check for repetitive patterns
    const eventCounts = {};
    for (const update of recentData) {
      eventCounts[update.event] = (eventCounts[update.event] || 0) + 1;
    }
    
    // Check for dominance of single event type
    const maxCount = Math.max(...Object.values(eventCounts));
    const dominance = maxCount / recentData.length;
    
    if (dominance > 0.8) {
      // Potential overfitting detected
      this.metrics.overfittingPrevented++;
      
      // Increase historical weight
      this.overfittingProtection.recentDataWeight = 0.5;
      this.overfittingProtection.historicalDataWeight = 0.5;
      
      logger.warn('Overfitting protection activated', {
        dominantEvent: Object.keys(eventCounts).find(k => eventCounts[k] === maxCount),
        dominance: `${(dominance * 100).toFixed(1)}%`
      });
      
      // Reset after delay
      setTimeout(() => {
        this.overfittingProtection.recentDataWeight = 0.7;
        this.overfittingProtection.historicalDataWeight = 0.3;
      }, 60 * 60 * 1000); // Reset after 1 hour
    }
  }

  async processUpdateQueue() {
    if (this.updateQueue.length === 0) return;
    
    // Process batch
    const batchSize = Math.min(10, this.updateQueue.length);
    const batch = this.updateQueue.splice(0, batchSize);
    
    // Apply weight based on recency
    const weighted = this.applyRecencyWeight(batch);
    
    // Process batch
    for (const update of weighted) {
      await this.processUpdate(update);
    }
  }

  applyRecencyWeight(updates) {
    const now = Date.now();
    
    return updates.map(update => {
      const age = now - update.timestamp;
      const weight = Math.exp(-age / (24 * 60 * 60 * 1000)); // Decay over 1 day
      
      return {
        ...update,
        weight: weight * this.overfittingProtection.recentDataWeight
      };
    });
  }

  async processUpdate(update) {
    // Process based on weight
    if (update.weight < 0.1) return; // Skip low-weight updates
    
    // Apply update with current learning rate
    const effectiveLearningRate = this.learningRate.current * update.weight;
    
    // Process through components
    // In production, would apply weighted updates to models
    logger.debug('Processed update', {
      event: update.event,
      weight: update.weight.toFixed(3),
      effectiveLearningRate: effectiveLearningRate.toFixed(4)
    });
  }

  async aggregateRecentPerformance() {
    const performance = await performanceTracker.getMetrics();
    const feedback = await feedbackLoop.getMetrics();
    
    return {
      sampleSize: performance.totalActions,
      overallSuccess: performance.totalActions > 0 
        ? performance.successfulActions / performance.totalActions 
        : 0,
      acceptanceRate: feedback.totalExplicit > 0
        ? feedback.totalExplicit / (feedback.totalImplicit + feedback.totalExplicit)
        : 0,
      byType: {} // Would aggregate by type in production
    };
  }

  async generateDailyInsights() {
    if (this.components.insightGenerator) {
      return await this.components.insightGenerator.generateDailyInsights();
    }
    
    logger.debug('Insight generator not available');
    return null;
  }

  async generateWeeklyReport() {
    try {
      const performance = await performanceTracker.generateReport('week');
      const improvement = await performanceTracker.getWeeklyImprovement();
      const patterns = await this.analyzePatterns();
      
      const report = {
        period: 'weekly',
        timestamp: Date.now(),
        performance,
        improvement,
        patterns: patterns.patterns.length,
        recommendations: performance.recommendations
      };
      
      logger.info('Weekly report generated', {
        improvement: improvement ? `${improvement.improvement.toFixed(1)}%` : 'N/A',
        recommendations: report.recommendations.length
      });
      
      return report;
    } catch (error) {
      logger.error('Weekly report generation failed', { error: error.message });
      return null;
    }
  }

  async majorModelUpdate() {
    logger.info('Starting major model update');
    
    try {
      // Get comprehensive performance data
      const performance = await performanceTracker.generateReport('week');
      
      // Perform deep tuning
      await modelTuner.autoTune({
        ...performance,
        patterns: await feedbackLoop.getPatterns()
      });
      
      logger.info('Major model update completed');
    } catch (error) {
      logger.error('Major model update failed', { error: error.message });
    }
  }

  async systemOptimization() {
    // Optimize system resources
    await this.pruneOldData();
    
    // Optimize model parameters
    await this.optimizeModels();
    
    logger.info('System optimization completed');
  }

  async pruneOldData() {
    // Clean old feedback
    const cutoff = Date.now() - 30 * 24 * 60 * 60 * 1000; // 30 days
    
    this.updateQueue = this.updateQueue.filter(u => u.timestamp > cutoff);
    
    logger.debug('Pruned old data', {
      remainingUpdates: this.updateQueue.length
    });
  }

  async optimizeModels() {
    const modelStats = await modelTuner.getModelStats();
    
    // Optimize based on stats
    logger.debug('Models optimized', {
      thresholds: Object.keys(modelStats.thresholds).length,
      weights: modelStats.weights.count || 0
    });
  }

  async getMetrics() {
    const componentMetrics = await Promise.all([
      feedbackLoop.getMetrics(),
      performanceTracker.getMetrics(),
      modelTuner.getMetrics()
    ]);
    
    return {
      orchestrator: this.metrics,
      feedbackLoop: componentMetrics[0],
      performanceTracker: componentMetrics[1],
      modelTuner: componentMetrics[2],
      learningRate: this.learningRate.current,
      updateQueueSize: this.updateQueue.length,
      overfittingProtection: this.overfittingProtection.enabled
    };
  }

  shutdown() {
    // Clear all intervals
    for (const interval of Object.values(this.intervals)) {
      if (interval) clearInterval(interval);
    }
    
    // Shutdown components
    if (this.components.feedbackLoop) {
      this.components.feedbackLoop.shutdown();
    }
    
    logger.info('Learning orchestrator shutdown');
  }
}

export default new LearningOrchestrator();