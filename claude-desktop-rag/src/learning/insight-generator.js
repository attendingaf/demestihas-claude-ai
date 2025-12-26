import winston from 'winston';
import { config } from '../../config/rag-config.js';
import persistentMemory from '../memory/advanced/persistent-memory.js';
import feedbackLoop from './feedback-loop.js';
import performanceTracker from './performance-tracker.js';
import modelTuner from './model-tuner.js';

const logger = winston.createLogger({
  level: config.logging.level,
  format: winston.format.json(),
  transports: [
    new winston.transports.Console(),
    new winston.transports.File({ filename: config.logging.file })
  ]
});

class InsightGenerator {
  constructor() {
    this.insights = new Map();
    this.weeklyInsights = [];
    this.actionableInsights = [];
    this.skillGaps = new Map();
    this.optimizationOpportunities = [];
    this.insightHistory = [];
    this.metrics = {
      totalInsights: 0,
      actionableInsights: 0,
      implementedSuggestions: 0,
      skillGapsIdentified: 0,
      optimizationsFound: 0
    };
  }

  async initialize() {
    logger.info('Initializing insight generator...');
    await this.loadHistoricalInsights();
    this.startPeriodicGeneration();
    logger.info('Insight generator initialized');
  }

  async extractActionableInsights(data) {
    const insights = [];
    const timestamp = Date.now();
    
    try {
      // Analyze patterns for insights
      if (data.patterns) {
        const patternInsights = await this.analyzePatterns(data.patterns);
        insights.push(...patternInsights);
      }
      
      // Analyze performance for insights
      if (data.performance) {
        const performanceInsights = await this.analyzePerformance(data.performance);
        insights.push(...performanceInsights);
      }
      
      // Analyze feedback for insights
      if (data.feedback) {
        const feedbackInsights = await this.analyzeFeedback(data.feedback);
        insights.push(...feedbackInsights);
      }
      
      // Filter for actionable insights
      const actionable = insights.filter(i => i.actionable && i.confidence > 0.7);
      
      // Store insights
      for (const insight of actionable) {
        const id = `insight_${timestamp}_${Math.random().toString(36).substr(2, 9)}`;
        insight.id = id;
        insight.timestamp = timestamp;
        
        this.insights.set(id, insight);
        this.actionableInsights.push(insight);
        this.metrics.actionableInsights++;
      }
      
      this.metrics.totalInsights += insights.length;
      
      logger.debug('Extracted actionable insights', {
        total: insights.length,
        actionable: actionable.length
      });
      
      return actionable;
    } catch (error) {
      logger.error('Failed to extract insights', { error: error.message });
      return [];
    }
  }

  async analyzePatterns(patterns) {
    const insights = [];
    
    for (const pattern of patterns) {
      // High-frequency patterns
      if (pattern.occurrences >= 10 && pattern.confidence > 0.8) {
        insights.push({
          type: 'pattern',
          category: 'automation_opportunity',
          title: 'Frequent Pattern Detected',
          description: `Pattern "${pattern.pattern}" occurs ${pattern.occurrences} times`,
          recommendation: 'Consider automating this workflow',
          actionable: true,
          confidence: pattern.confidence,
          impact: 'high',
          metadata: { pattern }
        });
      }
      
      // Inefficient patterns
      if (pattern.avgTimeSpent > 5000) {
        insights.push({
          type: 'pattern',
          category: 'optimization',
          title: 'Slow Pattern Identified',
          description: `Pattern "${pattern.pattern}" takes ${(pattern.avgTimeSpent / 1000).toFixed(1)}s on average`,
          recommendation: 'Optimize this workflow for better performance',
          actionable: true,
          confidence: 0.8,
          impact: 'medium',
          metadata: { pattern }
        });
      }
      
      // Error patterns
      if (pattern.signals && pattern.signals.filter(s => s === 'failure').length > pattern.signals.length * 0.3) {
        insights.push({
          type: 'pattern',
          category: 'quality',
          title: 'High Failure Rate Pattern',
          description: `Pattern "${pattern.pattern}" has ${(pattern.signals.filter(s => s === 'failure').length / pattern.signals.length * 100).toFixed(1)}% failure rate`,
          recommendation: 'Review and fix the underlying issue',
          actionable: true,
          confidence: 0.9,
          impact: 'high',
          metadata: { pattern }
        });
      }
    }
    
    return insights;
  }

  async analyzePerformance(performance) {
    const insights = [];
    
    // Overall performance trends
    if (performance.summary) {
      if (performance.summary.successRate < 0.5) {
        insights.push({
          type: 'performance',
          category: 'quality',
          title: 'Low Overall Success Rate',
          description: `System success rate is ${(performance.summary.successRate * 100).toFixed(1)}%`,
          recommendation: 'Review system configuration and error handling',
          actionable: true,
          confidence: 1.0,
          impact: 'critical',
          metadata: { performance: performance.summary }
        });
      }
      
      if (performance.summary.avgCompletionTime > 3000) {
        insights.push({
          type: 'performance',
          category: 'optimization',
          title: 'Slow Average Completion Time',
          description: `Average task completion takes ${(performance.summary.avgCompletionTime / 1000).toFixed(1)}s`,
          recommendation: 'Optimize slow operations and consider caching',
          actionable: true,
          confidence: 0.9,
          impact: 'high',
          metadata: { performance: performance.summary }
        });
      }
    }
    
    // Action-specific insights
    if (performance.actionBreakdown) {
      for (const [action, metrics] of Object.entries(performance.actionBreakdown)) {
        if (metrics.trend === 'declining') {
          insights.push({
            type: 'performance',
            category: 'regression',
            title: `Declining Performance: ${action}`,
            description: `${action} performance is declining (${(metrics.successRate * 100).toFixed(1)}% success rate)`,
            recommendation: `Investigate recent changes affecting ${action}`,
            actionable: true,
            confidence: 0.85,
            impact: 'medium',
            metadata: { action, metrics }
          });
        }
        
        if (metrics.successRate < 0.3 && metrics.total >= 5) {
          insights.push({
            type: 'performance',
            category: 'critical',
            title: `Critical: ${action} Failing`,
            description: `${action} has only ${(metrics.successRate * 100).toFixed(1)}% success rate`,
            recommendation: `Urgent: Fix ${action} implementation`,
            actionable: true,
            confidence: 1.0,
            impact: 'critical',
            metadata: { action, metrics }
          });
        }
      }
    }
    
    // Regression insights
    if (performance.regressions && performance.regressions.length > 0) {
      for (const regression of performance.regressions) {
        insights.push({
          type: 'performance',
          category: 'regression',
          title: 'Regression Detected',
          description: `Regression pattern: ${regression.pattern} (${regression.occurrences} occurrences)`,
          recommendation: 'Fix the regression to prevent further issues',
          actionable: true,
          confidence: 0.9,
          impact: regression.impact || 'high',
          metadata: { regression }
        });
      }
    }
    
    return insights;
  }

  async analyzeFeedback(feedback) {
    const insights = [];
    
    // Acceptance rate insights
    if (feedback.acceptanceRate !== undefined) {
      if (feedback.acceptanceRate < 0.4) {
        insights.push({
          type: 'feedback',
          category: 'user_experience',
          title: 'Low Suggestion Acceptance',
          description: `Only ${(feedback.acceptanceRate * 100).toFixed(1)}% of suggestions are accepted`,
          recommendation: 'Improve suggestion relevance and timing',
          actionable: true,
          confidence: 0.9,
          impact: 'high',
          metadata: { acceptanceRate: feedback.acceptanceRate }
        });
      }
      
      if (feedback.acceptanceRate > 0.8) {
        insights.push({
          type: 'feedback',
          category: 'success',
          title: 'High Suggestion Acceptance',
          description: `${(feedback.acceptanceRate * 100).toFixed(1)}% acceptance rate indicates good model performance`,
          recommendation: 'Maintain current approach and consider expanding suggestions',
          actionable: false,
          confidence: 0.9,
          impact: 'positive',
          metadata: { acceptanceRate: feedback.acceptanceRate }
        });
      }
    }
    
    // Correlation insights
    if (feedback.correlations) {
      for (const [key, data] of Object.entries(feedback.correlations)) {
        if (data.avgCorrelation > 0.8 && data.count >= 5) {
          insights.push({
            type: 'feedback',
            category: 'pattern',
            title: 'Strong Correlation Found',
            description: `Strong correlation (${(data.avgCorrelation * 100).toFixed(1)}%) for ${key}`,
            recommendation: `Use this correlation to improve predictions for ${key}`,
            actionable: true,
            confidence: data.avgCorrelation,
            impact: 'medium',
            metadata: { correlation: key, data }
          });
        }
      }
    }
    
    return insights;
  }

  async generateWeeklySummary() {
    try {
      // Get data from all components
      const [
        performanceReport,
        feedbackMetrics,
        modelStats,
        patterns
      ] = await Promise.all([
        performanceTracker.generateReport('week'),
        feedbackLoop.getMetrics(),
        modelTuner.getMetrics(),
        feedbackLoop.getPatterns()
      ]);
      
      // Extract insights from all data
      const insights = await this.extractActionableInsights({
        performance: performanceReport,
        feedback: feedbackMetrics,
        patterns
      });
      
      // Identify skill gaps
      const skillGaps = await this.identifySkillGaps(performanceReport);
      
      // Find optimization opportunities
      const optimizations = await this.findOptimizationOpportunities({
        performance: performanceReport,
        modelStats
      });
      
      // Create weekly summary
      const summary = {
        week: this.getWeekNumber(),
        timestamp: Date.now(),
        insights: insights.length,
        topInsights: insights.slice(0, 5),
        skillGaps,
        optimizations,
        metrics: {
          successRate: performanceReport.summary.successRate,
          improvement: await performanceTracker.getWeeklyImprovement(),
          patternsIdentified: patterns.length,
          actionableInsights: insights.filter(i => i.actionable).length
        },
        recommendations: this.generateWeeklyRecommendations(insights, skillGaps, optimizations)
      };
      
      // Store weekly summary
      this.weeklyInsights.push(summary);
      
      logger.info('Generated weekly summary', {
        insights: summary.insights,
        skillGaps: skillGaps.length,
        optimizations: optimizations.length
      });
      
      return summary;
    } catch (error) {
      logger.error('Failed to generate weekly summary', { error: error.message });
      return null;
    }
  }

  async identifySkillGaps(performance) {
    const gaps = [];
    
    // Analyze action success rates
    if (performance.actionBreakdown) {
      for (const [action, metrics] of Object.entries(performance.actionBreakdown)) {
        if (metrics.successRate < 0.5 && metrics.total >= 5) {
          const gap = {
            area: action,
            currentLevel: metrics.successRate,
            targetLevel: 0.8,
            gap: 0.8 - metrics.successRate,
            priority: metrics.total > 20 ? 'high' : 'medium',
            recommendation: `Improve ${action} skills through practice or training`
          };
          
          gaps.push(gap);
          this.skillGaps.set(action, gap);
        }
      }
    }
    
    // Analyze error patterns
    if (performance.regressions) {
      for (const regression of performance.regressions) {
        const area = regression.pattern.split(':')[0];
        if (!this.skillGaps.has(area)) {
          const gap = {
            area,
            issue: 'Recurring errors',
            priority: 'high',
            recommendation: `Learn to handle ${area} errors better`
          };
          
          gaps.push(gap);
          this.skillGaps.set(area, gap);
        }
      }
    }
    
    this.metrics.skillGapsIdentified = gaps.length;
    
    return gaps;
  }

  async findOptimizationOpportunities(data) {
    const opportunities = [];
    
    // Performance optimizations
    if (data.performance?.actionBreakdown) {
      for (const [action, metrics] of Object.entries(data.performance.actionBreakdown)) {
        if (metrics.avgTime > 2000) {
          opportunities.push({
            type: 'performance',
            target: action,
            currentTime: metrics.avgTime,
            potentialSaving: metrics.avgTime * 0.3,
            method: 'caching',
            priority: metrics.total > 50 ? 'high' : 'medium',
            description: `Optimize ${action} by implementing caching`
          });
        }
      }
    }
    
    // Model optimizations
    if (data.modelStats) {
      if (data.modelStats.activeWeights > 100) {
        opportunities.push({
          type: 'model',
          target: 'pattern_weights',
          currentSize: data.modelStats.activeWeights,
          potentialReduction: data.modelStats.activeWeights * 0.2,
          method: 'pruning',
          priority: 'low',
          description: 'Prune low-confidence pattern weights'
        });
      }
    }
    
    // System optimizations
    if (data.performance?.summary?.totalActions > 10000) {
      opportunities.push({
        type: 'system',
        target: 'data_storage',
        method: 'archiving',
        priority: 'medium',
        description: 'Archive old performance data to reduce memory usage'
      });
    }
    
    this.optimizationOpportunities = opportunities;
    this.metrics.optimizationsFound = opportunities.length;
    
    return opportunities;
  }

  generateWeeklyRecommendations(insights, skillGaps, optimizations) {
    const recommendations = [];
    
    // Top priority from insights
    const criticalInsights = insights.filter(i => i.impact === 'critical');
    if (criticalInsights.length > 0) {
      recommendations.push({
        priority: 1,
        category: 'critical',
        action: criticalInsights[0].recommendation,
        reason: criticalInsights[0].description
      });
    }
    
    // Address skill gaps
    const highPriorityGaps = skillGaps.filter(g => g.priority === 'high');
    if (highPriorityGaps.length > 0) {
      recommendations.push({
        priority: 2,
        category: 'skill_development',
        action: highPriorityGaps[0].recommendation,
        reason: `Bridge skill gap in ${highPriorityGaps[0].area}`
      });
    }
    
    // Performance optimizations
    const highPriorityOpts = optimizations.filter(o => o.priority === 'high');
    if (highPriorityOpts.length > 0) {
      recommendations.push({
        priority: 3,
        category: 'optimization',
        action: highPriorityOpts[0].description,
        reason: `Save ${(highPriorityOpts[0].potentialSaving / 1000).toFixed(1)}s per operation`
      });
    }
    
    // General improvements
    if (insights.length > 10) {
      recommendations.push({
        priority: 4,
        category: 'systematic',
        action: 'Review and implement top actionable insights',
        reason: `${insights.filter(i => i.actionable).length} actionable improvements available`
      });
    }
    
    return recommendations.slice(0, 5); // Top 5 recommendations
  }

  async suggestSystemOptimizations() {
    const suggestions = [];
    
    // Get current metrics
    const metrics = await this.getAllMetrics();
    
    // Memory optimization
    if (metrics.memoryUsage > 500) {
      suggestions.push({
        type: 'memory',
        action: 'Enable memory compression',
        impact: 'Reduce memory usage by ~30%',
        complexity: 'low'
      });
    }
    
    // Performance optimization
    if (metrics.avgResponseTime > 100) {
      suggestions.push({
        type: 'performance',
        action: 'Implement request batching',
        impact: 'Reduce response time by ~40%',
        complexity: 'medium'
      });
    }
    
    // Model optimization
    if (metrics.modelCount > 20) {
      suggestions.push({
        type: 'model',
        action: 'Consolidate similar models',
        impact: 'Reduce model count by ~25%',
        complexity: 'high'
      });
    }
    
    return suggestions;
  }

  async generateDailyInsights() {
    try {
      const [performance, feedback] = await Promise.all([
        performanceTracker.generateReport('day'),
        feedbackLoop.getMetrics()
      ]);
      
      const insights = await this.extractActionableInsights({
        performance,
        feedback
      });
      
      const daily = {
        date: new Date().toISOString().split('T')[0],
        insights: insights.slice(0, 3),
        metrics: {
          successRate: performance.summary.successRate,
          totalActions: performance.summary.totalActions,
          acceptanceRate: feedback.totalExplicit > 0
            ? feedback.totalExplicit / (feedback.totalImplicit + feedback.totalExplicit)
            : 0
        }
      };
      
      logger.info('Generated daily insights', {
        count: daily.insights.length
      });
      
      return daily;
    } catch (error) {
      logger.error('Failed to generate daily insights', { error: error.message });
      return null;
    }
  }

  getWeekNumber() {
    const now = new Date();
    const start = new Date(now.getFullYear(), 0, 1);
    const diff = now - start;
    const oneWeek = 1000 * 60 * 60 * 24 * 7;
    return Math.floor(diff / oneWeek) + 1;
  }

  async getAllMetrics() {
    // Aggregate metrics from all sources
    const [perf, feedback, model] = await Promise.all([
      performanceTracker.getMetrics(),
      feedbackLoop.getMetrics(),
      modelTuner.getMetrics()
    ]);
    
    return {
      memoryUsage: process.memoryUsage().heapUsed / 1024 / 1024,
      avgResponseTime: perf.avgCompletionTime,
      modelCount: model.rankingModels + model.predictionModels,
      ...perf,
      ...feedback
    };
  }

  async loadHistoricalInsights() {
    try {
      const memories = await persistentMemory.getUserMemories('system');
      
      for (const memory of memories) {
        if (memory.type === 'fact' && memory.content.includes('insight')) {
          this.insightHistory.push({
            content: memory.content,
            timestamp: memory.timestamp
          });
        }
      }
      
      logger.debug(`Loaded ${this.insightHistory.length} historical insights`);
    } catch (error) {
      logger.error('Failed to load historical insights', { error: error.message });
    }
  }

  startPeriodicGeneration() {
    // Daily insight generation
    setInterval(async () => {
      await this.generateDailyInsights();
    }, 24 * 60 * 60 * 1000);
    
    // Weekly summary generation
    setInterval(async () => {
      await this.generateWeeklySummary();
    }, 7 * 24 * 60 * 60 * 1000);
  }

  async getMetrics() {
    return {
      ...this.metrics,
      currentInsights: this.insights.size,
      weeklyReports: this.weeklyInsights.length,
      activeSkillGaps: this.skillGaps.size,
      pendingOptimizations: this.optimizationOpportunities.length
    };
  }
}

export default new InsightGenerator();