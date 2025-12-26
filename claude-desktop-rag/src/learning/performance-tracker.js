import winston from 'winston';
import { performance } from 'perf_hooks';
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

class PerformanceTracker {
  constructor() {
    this.actionMetrics = new Map();
    this.completionTimes = new Map();
    this.regressionPatterns = new Map();
    this.performanceHistory = [];
    this.weeklyMetrics = {
      current: this.initWeekMetrics(),
      previous: this.initWeekMetrics()
    };
    this.metrics = {
      totalActions: 0,
      successfulActions: 0,
      failedActions: 0,
      avgCompletionTime: 0,
      regressionCount: 0
    };
  }

  async initialize() {
    logger.info('Initializing performance tracker...');
    await this.loadHistoricalMetrics();
    this.startPeriodicAnalysis();
    logger.info('Performance tracker initialized');
  }

  async trackAction(actionType, success, completionTime, context = {}) {
    const timestamp = Date.now();
    
    // Update action metrics
    if (!this.actionMetrics.has(actionType)) {
      this.actionMetrics.set(actionType, {
        total: 0,
        successful: 0,
        failed: 0,
        avgTime: 0,
        successRate: 0,
        trend: 'stable'
      });
    }
    
    const actionMetric = this.actionMetrics.get(actionType);
    actionMetric.total++;
    
    if (success) {
      actionMetric.successful++;
      this.metrics.successfulActions++;
    } else {
      actionMetric.failed++;
      this.metrics.failedActions++;
      
      // Check for regression
      await this.checkRegression(actionType, context);
    }
    
    // Update completion time
    if (completionTime) {
      actionMetric.avgTime = 
        (actionMetric.avgTime * (actionMetric.total - 1) + completionTime) / actionMetric.total;
      
      this.trackCompletionTime(actionType, completionTime);
    }
    
    // Calculate success rate
    actionMetric.successRate = actionMetric.successful / actionMetric.total;
    
    // Update trend
    actionMetric.trend = await this.calculateTrend(actionType);
    
    // Update global metrics
    this.metrics.totalActions++;
    this.updateGlobalMetrics(completionTime);
    
    // Update weekly metrics
    this.updateWeeklyMetrics(actionType, success, completionTime);
    
    // Store in history
    this.performanceHistory.push({
      timestamp,
      actionType,
      success,
      completionTime,
      context
    });
    
    // Clean old history
    this.cleanOldHistory();
    
    logger.debug('Tracked action performance', {
      actionType,
      success,
      completionTime,
      successRate: actionMetric.successRate.toFixed(2)
    });
    
    return {
      successRate: actionMetric.successRate,
      trend: actionMetric.trend
    };
  }

  trackCompletionTime(actionType, time) {
    if (!this.completionTimes.has(actionType)) {
      this.completionTimes.set(actionType, []);
    }
    
    const times = this.completionTimes.get(actionType);
    times.push({
      time,
      timestamp: Date.now()
    });
    
    // Keep only recent times (last 100)
    if (times.length > 100) {
      times.shift();
    }
  }

  async calculateTrend(actionType) {
    const metric = this.actionMetrics.get(actionType);
    if (!metric || metric.total < 10) return 'stable';
    
    // Get recent history
    const recentActions = this.performanceHistory
      .filter(h => h.actionType === actionType)
      .slice(-20);
    
    if (recentActions.length < 10) return 'stable';
    
    // Calculate success rate for first and second half
    const midpoint = Math.floor(recentActions.length / 2);
    const firstHalf = recentActions.slice(0, midpoint);
    const secondHalf = recentActions.slice(midpoint);
    
    const firstSuccessRate = firstHalf.filter(a => a.success).length / firstHalf.length;
    const secondSuccessRate = secondHalf.filter(a => a.success).length / secondHalf.length;
    
    const difference = secondSuccessRate - firstSuccessRate;
    
    if (difference > 0.1) return 'improving';
    if (difference < -0.1) return 'declining';
    return 'stable';
  }

  async checkRegression(actionType, context) {
    const key = `${actionType}:${context.errorType || 'unknown'}`;
    
    if (!this.regressionPatterns.has(key)) {
      this.regressionPatterns.set(key, {
        pattern: key,
        occurrences: 0,
        firstSeen: Date.now(),
        lastSeen: Date.now(),
        contexts: []
      });
    }
    
    const regression = this.regressionPatterns.get(key);
    regression.occurrences++;
    regression.lastSeen = Date.now();
    regression.contexts.push(context);
    
    // Keep only recent contexts
    if (regression.contexts.length > 10) {
      regression.contexts.shift();
    }
    
    // Mark as regression if frequent
    if (regression.occurrences >= 3) {
      this.metrics.regressionCount++;
      
      logger.warn('Regression pattern detected', {
        pattern: key,
        occurrences: regression.occurrences
      });
      
      // Store regression for analysis
      await this.storeRegression(regression);
    }
  }

  async storeRegression(regression) {
    try {
      await persistentMemory.consolidateSession('system', {
        interactions: [{
          type: 'regression',
          content: regression.pattern,
          metadata: {
            occurrences: regression.occurrences,
            duration: regression.lastSeen - regression.firstSeen
          }
        }],
        facts: [`Regression detected: ${regression.pattern}`]
      });
    } catch (error) {
      logger.error('Failed to store regression', { error: error.message });
    }
  }

  updateGlobalMetrics(completionTime) {
    if (completionTime) {
      const total = this.metrics.totalActions;
      this.metrics.avgCompletionTime = 
        (this.metrics.avgCompletionTime * (total - 1) + completionTime) / total;
    }
  }

  updateWeeklyMetrics(actionType, success, completionTime) {
    const week = this.weeklyMetrics.current;
    
    week.totalActions++;
    if (success) {
      week.successfulActions++;
    }
    
    if (completionTime) {
      week.totalCompletionTime += completionTime;
    }
    
    // Update action breakdown
    if (!week.actionBreakdown[actionType]) {
      week.actionBreakdown[actionType] = {
        count: 0,
        successes: 0
      };
    }
    
    week.actionBreakdown[actionType].count++;
    if (success) {
      week.actionBreakdown[actionType].successes++;
    }
  }

  async generateReport(period = 'week') {
    const report = {
      period,
      timestamp: Date.now(),
      summary: {},
      actionBreakdown: {},
      trends: {},
      regressions: [],
      recommendations: []
    };
    
    // Calculate summary metrics
    const overallSuccessRate = this.metrics.successfulActions / this.metrics.totalActions;
    
    report.summary = {
      totalActions: this.metrics.totalActions,
      successRate: overallSuccessRate,
      avgCompletionTime: this.metrics.avgCompletionTime,
      regressionCount: this.metrics.regressionCount
    };
    
    // Action breakdown
    for (const [actionType, metric] of this.actionMetrics.entries()) {
      report.actionBreakdown[actionType] = {
        total: metric.total,
        successRate: metric.successRate,
        avgTime: metric.avgTime,
        trend: metric.trend
      };
      
      report.trends[actionType] = metric.trend;
    }
    
    // Regression patterns
    for (const regression of this.regressionPatterns.values()) {
      if (regression.occurrences >= 3) {
        report.regressions.push({
          pattern: regression.pattern,
          occurrences: regression.occurrences,
          impact: 'high'
        });
      }
    }
    
    // Generate recommendations
    report.recommendations = this.generateRecommendations(report);
    
    logger.info('Generated performance report', {
      period,
      actionsTracked: report.summary.totalActions,
      successRate: `${(overallSuccessRate * 100).toFixed(1)}%`
    });
    
    return report;
  }

  generateRecommendations(report) {
    const recommendations = [];
    
    // Check for low success rates
    for (const [actionType, metrics] of Object.entries(report.actionBreakdown)) {
      if (metrics.successRate < 0.5) {
        recommendations.push({
          type: 'improvement',
          action: actionType,
          message: `Success rate for ${actionType} is low (${(metrics.successRate * 100).toFixed(1)}%). Consider reviewing implementation.`
        });
      }
      
      if (metrics.avgTime > 5000) {
        recommendations.push({
          type: 'optimization',
          action: actionType,
          message: `${actionType} takes ${(metrics.avgTime / 1000).toFixed(1)}s on average. Consider optimization.`
        });
      }
    }
    
    // Check for regressions
    if (report.regressions.length > 0) {
      recommendations.push({
        type: 'regression',
        message: `${report.regressions.length} regression patterns detected. Review error handling.`
      });
    }
    
    return recommendations;
  }

  async getSuccessRate(actionType = null) {
    if (actionType) {
      const metric = this.actionMetrics.get(actionType);
      return metric ? metric.successRate : 0;
    }
    
    return this.metrics.totalActions > 0 
      ? this.metrics.successfulActions / this.metrics.totalActions
      : 0;
  }

  async getCompletionTimeStats(actionType = null) {
    if (actionType) {
      const times = this.completionTimes.get(actionType);
      if (!times || times.length === 0) return null;
      
      const values = times.map(t => t.time);
      return {
        avg: values.reduce((a, b) => a + b, 0) / values.length,
        min: Math.min(...values),
        max: Math.max(...values),
        p50: this.percentile(values, 0.5),
        p95: this.percentile(values, 0.95)
      };
    }
    
    return {
      avg: this.metrics.avgCompletionTime,
      totalActions: this.metrics.totalActions
    };
  }

  percentile(values, p) {
    const sorted = values.slice().sort((a, b) => a - b);
    const index = Math.floor(sorted.length * p);
    return sorted[index];
  }

  async getRegressionPatterns() {
    return Array.from(this.regressionPatterns.values())
      .filter(r => r.occurrences >= 2)
      .sort((a, b) => b.occurrences - a.occurrences);
  }

  initWeekMetrics() {
    return {
      startTime: Date.now(),
      totalActions: 0,
      successfulActions: 0,
      totalCompletionTime: 0,
      actionBreakdown: {}
    };
  }

  rotateWeeklyMetrics() {
    this.weeklyMetrics.previous = this.weeklyMetrics.current;
    this.weeklyMetrics.current = this.initWeekMetrics();
    
    logger.info('Rotated weekly metrics');
  }

  async getWeeklyImprovement() {
    const current = this.weeklyMetrics.current;
    const previous = this.weeklyMetrics.previous;
    
    if (previous.totalActions === 0) return null;
    
    const currentSuccessRate = current.successfulActions / current.totalActions;
    const previousSuccessRate = previous.successfulActions / previous.totalActions;
    
    const improvement = ((currentSuccessRate - previousSuccessRate) / previousSuccessRate) * 100;
    
    return {
      improvement,
      currentSuccessRate,
      previousSuccessRate,
      actionComparison: this.compareActionBreakdown(current.actionBreakdown, previous.actionBreakdown)
    };
  }

  compareActionBreakdown(current, previous) {
    const comparison = {};
    
    const allActions = new Set([...Object.keys(current), ...Object.keys(previous)]);
    
    for (const action of allActions) {
      const curr = current[action] || { count: 0, successes: 0 };
      const prev = previous[action] || { count: 0, successes: 0 };
      
      const currRate = curr.count > 0 ? curr.successes / curr.count : 0;
      const prevRate = prev.count > 0 ? prev.successes / prev.count : 0;
      
      comparison[action] = {
        current: currRate,
        previous: prevRate,
        change: currRate - prevRate
      };
    }
    
    return comparison;
  }

  async loadHistoricalMetrics() {
    try {
      const memories = await persistentMemory.getUserMemories('system');
      
      for (const memory of memories) {
        if (memory.type === 'pattern' && memory.content.includes('performance')) {
          // Load historical performance data
          logger.debug('Loaded historical performance data');
        }
      }
    } catch (error) {
      logger.error('Failed to load historical metrics', { error: error.message });
    }
  }

  startPeriodicAnalysis() {
    // Weekly rotation
    setInterval(() => {
      this.rotateWeeklyMetrics();
    }, 7 * 24 * 60 * 60 * 1000);
    
    // Hourly cleanup
    setInterval(() => {
      this.cleanOldHistory();
      this.cleanOldRegressions();
    }, 60 * 60 * 1000);
  }

  cleanOldHistory() {
    const cutoff = Date.now() - 30 * 24 * 60 * 60 * 1000; // 30 days
    
    this.performanceHistory = this.performanceHistory.filter(
      h => h.timestamp > cutoff
    );
  }

  cleanOldRegressions() {
    const cutoff = Date.now() - 7 * 24 * 60 * 60 * 1000; // 7 days
    
    for (const [key, regression] of this.regressionPatterns.entries()) {
      if (regression.lastSeen < cutoff) {
        this.regressionPatterns.delete(key);
      }
    }
  }

  async getMetrics() {
    const weeklyImprovement = await this.getWeeklyImprovement();
    
    return {
      ...this.metrics,
      actionTypes: this.actionMetrics.size,
      activeRegressions: this.regressionPatterns.size,
      weeklyImprovement: weeklyImprovement?.improvement || 0,
      performanceHistorySize: this.performanceHistory.length
    };
  }
}

export default new PerformanceTracker();