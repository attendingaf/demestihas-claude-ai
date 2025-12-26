import winston from 'winston';
import { v4 as uuidv4 } from 'uuid';
import { performance } from 'perf_hooks';
import { config } from '../../config/rag-config.js';
import persistentMemory from '../memory/advanced/persistent-memory.js';
import proactiveMind from '../proactive/proactive-mind.js';

const logger = winston.createLogger({
  level: config.logging.level,
  format: winston.format.json(),
  transports: [
    new winston.transports.Console(),
    new winston.transports.File({ filename: config.logging.file })
  ]
});

class FeedbackLoop {
  constructor() {
    this.implicitFeedback = new Map();
    this.explicitFeedback = new Map();
    this.actionCorrelations = new Map();
    this.feedbackPatterns = new Map();
    this.sessionTracking = new Map();
    this.metrics = {
      totalImplicit: 0,
      totalExplicit: 0,
      correlatedActions: 0,
      patternsIdentified: 0,
      avgProcessingTime: 0
    };
    this.captureInterval = null;
  }

  async initialize() {
    logger.info('Initializing feedback loop engine...');
    await this.loadHistoricalPatterns();
    this.startImplicitCapture();
    logger.info('Feedback loop engine initialized');
  }

  async captureImplicitFeedback(action, context = {}) {
    const startTime = performance.now();
    const feedbackId = uuidv4();
    
    const feedback = {
      id: feedbackId,
      type: 'implicit',
      action,
      timestamp: Date.now(),
      context,
      metrics: {
        timeSpent: 0,
        editsMode: 0,
        reruns: 0,
        abandoned: false
      }
    };
    
    // Start tracking session
    if (context.sessionId) {
      this.trackSession(context.sessionId, feedback);
    }
    
    // Detect feedback type
    if (action.type === 'edit') {
      feedback.metrics.editsMode++;
      feedback.signal = 'modification';
    } else if (action.type === 'rerun') {
      feedback.metrics.reruns++;
      feedback.signal = 'retry';
    } else if (action.type === 'complete') {
      feedback.signal = 'success';
    } else if (action.type === 'abandon') {
      feedback.metrics.abandoned = true;
      feedback.signal = 'failure';
    }
    
    // Calculate time spent
    if (this.sessionTracking.has(context.sessionId)) {
      const session = this.sessionTracking.get(context.sessionId);
      feedback.metrics.timeSpent = Date.now() - session.startTime;
    }
    
    // Store feedback
    this.implicitFeedback.set(feedbackId, feedback);
    this.metrics.totalImplicit++;
    
    // Correlate with recent actions
    await this.correlateWithActions(feedback);
    
    // Detect patterns
    await this.detectFeedbackPattern(feedback);
    
    // Update metrics
    const processingTime = performance.now() - startTime;
    this.updateMetrics(processingTime);
    
    logger.debug('Captured implicit feedback', {
      id: feedbackId,
      signal: feedback.signal,
      timeSpent: feedback.metrics.timeSpent
    });
    
    return feedbackId;
  }

  async captureExplicitFeedback(rating, correction = null, context = {}) {
    const feedbackId = uuidv4();
    
    const feedback = {
      id: feedbackId,
      type: 'explicit',
      rating,
      correction,
      timestamp: Date.now(),
      context,
      processed: false
    };
    
    // Interpret rating
    if (rating >= 4) {
      feedback.signal = 'positive';
    } else if (rating >= 3) {
      feedback.signal = 'neutral';
    } else {
      feedback.signal = 'negative';
    }
    
    // Process correction if provided
    if (correction) {
      feedback.correctionType = this.analyzeCorrectionType(correction);
    }
    
    // Store feedback
    this.explicitFeedback.set(feedbackId, feedback);
    this.metrics.totalExplicit++;
    
    // Immediate processing for explicit feedback
    await this.processExplicitFeedback(feedback);
    
    logger.info('Captured explicit feedback', {
      id: feedbackId,
      rating,
      signal: feedback.signal,
      hasCorrection: !!correction
    });
    
    return feedbackId;
  }

  async correlateWithActions(feedback) {
    try {
      // Get recent actions from proactive mind
      const recentActions = await this.getRecentActions(feedback.context);
      
      if (recentActions.length === 0) return;
      
      // Find correlations
      const correlations = [];
      
      for (const action of recentActions) {
        const correlation = this.calculateCorrelation(feedback, action);
        
        if (correlation > 0.5) {
          correlations.push({
            actionId: action.id,
            feedbackId: feedback.id,
            correlation,
            actionType: action.type,
            feedbackSignal: feedback.signal
          });
        }
      }
      
      // Store correlations
      for (const corr of correlations) {
        const key = `${corr.actionType}:${corr.feedbackSignal}`;
        
        if (!this.actionCorrelations.has(key)) {
          this.actionCorrelations.set(key, []);
        }
        
        this.actionCorrelations.get(key).push(corr);
        this.metrics.correlatedActions++;
      }
      
      logger.debug('Correlated feedback with actions', {
        feedbackId: feedback.id,
        correlations: correlations.length
      });
      
    } catch (error) {
      logger.error('Failed to correlate actions', { error: error.message });
    }
  }

  async detectFeedbackPattern(feedback) {
    const patternKey = this.generatePatternKey(feedback);
    
    if (!this.feedbackPatterns.has(patternKey)) {
      this.feedbackPatterns.set(patternKey, {
        pattern: patternKey,
        occurrences: 0,
        signals: [],
        avgTimeSpent: 0,
        confidence: 0.5
      });
    }
    
    const pattern = this.feedbackPatterns.get(patternKey);
    pattern.occurrences++;
    pattern.signals.push(feedback.signal);
    
    // Update average time spent
    if (feedback.metrics?.timeSpent) {
      pattern.avgTimeSpent = 
        (pattern.avgTimeSpent * (pattern.occurrences - 1) + feedback.metrics.timeSpent) / 
        pattern.occurrences;
    }
    
    // Calculate pattern confidence
    pattern.confidence = this.calculatePatternConfidence(pattern);
    
    // Store significant patterns
    if (pattern.occurrences >= 3 && pattern.confidence > 0.6) {
      await this.storePattern(pattern);
      this.metrics.patternsIdentified++;
    }
  }

  async storePattern(pattern) {
    try {
      // Store in persistent memory
      await persistentMemory.consolidateSession('system', {
        interactions: [{
          type: 'feedback_pattern',
          content: pattern.pattern,
          metadata: {
            occurrences: pattern.occurrences,
            confidence: pattern.confidence,
            avgTimeSpent: pattern.avgTimeSpent
          }
        }],
        facts: [`Feedback pattern detected: ${pattern.pattern}`]
      });
      
      logger.debug('Stored feedback pattern', {
        pattern: pattern.pattern,
        confidence: pattern.confidence
      });
    } catch (error) {
      logger.error('Failed to store pattern', { error: error.message });
    }
  }

  trackSession(sessionId, feedback) {
    if (!this.sessionTracking.has(sessionId)) {
      this.sessionTracking.set(sessionId, {
        sessionId,
        startTime: Date.now(),
        feedbacks: [],
        actions: []
      });
    }
    
    const session = this.sessionTracking.get(sessionId);
    session.feedbacks.push(feedback.id);
    
    // Clean old sessions
    this.cleanOldSessions();
  }

  async processExplicitFeedback(feedback) {
    // Update related implicit feedback
    const relatedImplicit = this.findRelatedImplicitFeedback(feedback);
    
    for (const implicit of relatedImplicit) {
      implicit.explicitRating = feedback.rating;
      implicit.validated = true;
    }
    
    // Apply corrections if provided
    if (feedback.correction) {
      await this.applyCorrection(feedback.correction, feedback.correctionType);
    }
    
    feedback.processed = true;
  }

  findRelatedImplicitFeedback(explicitFeedback) {
    const related = [];
    const timeWindow = 5 * 60 * 1000; // 5 minutes
    
    for (const implicit of this.implicitFeedback.values()) {
      const timeDiff = Math.abs(implicit.timestamp - explicitFeedback.timestamp);
      
      if (timeDiff < timeWindow && 
          implicit.context?.sessionId === explicitFeedback.context?.sessionId) {
        related.push(implicit);
      }
    }
    
    return related;
  }

  async applyCorrection(correction, type) {
    logger.info('Applying correction', { type });
    
    // In production, would update models based on correction type
    switch (type) {
      case 'parameter':
        // Update parameter suggestions
        break;
      case 'sequence':
        // Update action sequences
        break;
      case 'timing':
        // Update timing predictions
        break;
      default:
        // General correction
        break;
    }
  }

  analyzeCorrectionType(correction) {
    if (typeof correction !== 'string') return 'general';
    
    const lower = correction.toLowerCase();
    
    if (lower.includes('parameter') || lower.includes('value')) {
      return 'parameter';
    }
    if (lower.includes('order') || lower.includes('sequence')) {
      return 'sequence';
    }
    if (lower.includes('time') || lower.includes('when')) {
      return 'timing';
    }
    
    return 'general';
  }

  calculateCorrelation(feedback, action) {
    let correlation = 0;
    
    // Time proximity
    const timeDiff = Math.abs(feedback.timestamp - action.timestamp);
    const timeCorr = Math.exp(-timeDiff / (60 * 1000)); // Decay over 1 minute
    correlation += timeCorr * 0.4;
    
    // Context similarity
    if (feedback.context?.sessionId === action.context?.sessionId) {
      correlation += 0.3;
    }
    
    // Action type match
    if (feedback.action?.type === action.type) {
      correlation += 0.3;
    }
    
    return Math.min(correlation, 1.0);
  }

  generatePatternKey(feedback) {
    const components = [];
    
    if (feedback.signal) {
      components.push(feedback.signal);
    }
    
    if (feedback.action?.type) {
      components.push(feedback.action.type);
    }
    
    if (feedback.metrics?.abandoned) {
      components.push('abandoned');
    }
    
    return components.join(':') || 'unknown';
  }

  calculatePatternConfidence(pattern) {
    let confidence = 0.5;
    
    // Frequency factor
    confidence += Math.min(pattern.occurrences / 10, 0.2);
    
    // Consistency factor
    const signalCounts = {};
    for (const signal of pattern.signals) {
      signalCounts[signal] = (signalCounts[signal] || 0) + 1;
    }
    
    const maxSignalCount = Math.max(...Object.values(signalCounts));
    const consistency = maxSignalCount / pattern.signals.length;
    confidence += consistency * 0.3;
    
    return Math.min(confidence, 1.0);
  }

  async getRecentActions(context) {
    // In production, would query from proactive mind
    // For now, return mock data
    return [];
  }

  async loadHistoricalPatterns() {
    try {
      // Load patterns from persistent memory
      const patterns = await persistentMemory.getUserMemories('system');
      
      for (const memory of patterns) {
        if (memory.type === 'pattern' && memory.content.includes('feedback')) {
          this.feedbackPatterns.set(memory.content, {
            pattern: memory.content,
            occurrences: memory.frequency || 1,
            confidence: memory.confidence || 0.5
          });
        }
      }
      
      logger.debug(`Loaded ${this.feedbackPatterns.size} historical patterns`);
    } catch (error) {
      logger.error('Failed to load historical patterns', { error: error.message });
    }
  }

  startImplicitCapture() {
    // Start periodic implicit feedback capture
    this.captureInterval = setInterval(async () => {
      await this.capturePeriodicMetrics();
    }, 30000); // Every 30 seconds
  }

  async capturePeriodicMetrics() {
    // Capture system-wide metrics
    const sessions = Array.from(this.sessionTracking.values());
    
    for (const session of sessions) {
      const duration = Date.now() - session.startTime;
      
      if (duration > 5 * 60 * 1000) { // Sessions over 5 minutes
        await this.captureImplicitFeedback(
          { type: 'long_session' },
          { sessionId: session.sessionId }
        );
      }
    }
  }

  cleanOldSessions() {
    const cutoff = Date.now() - 60 * 60 * 1000; // 1 hour
    
    for (const [sessionId, session] of this.sessionTracking.entries()) {
      if (session.startTime < cutoff) {
        this.sessionTracking.delete(sessionId);
      }
    }
  }

  updateMetrics(processingTime) {
    const total = this.metrics.totalImplicit + this.metrics.totalExplicit;
    this.metrics.avgProcessingTime = 
      (this.metrics.avgProcessingTime * (total - 1) + processingTime) / total;
  }

  async getPatterns() {
    return Array.from(this.feedbackPatterns.values())
      .filter(p => p.confidence > 0.6)
      .sort((a, b) => b.confidence - a.confidence);
  }

  async getCorrelations() {
    const correlations = {};
    
    for (const [key, values] of this.actionCorrelations.entries()) {
      correlations[key] = {
        count: values.length,
        avgCorrelation: values.reduce((sum, v) => sum + v.correlation, 0) / values.length
      };
    }
    
    return correlations;
  }

  async getMetrics() {
    const patterns = await this.getPatterns();
    const correlations = await this.getCorrelations();
    
    return {
      ...this.metrics,
      activeSessions: this.sessionTracking.size,
      highConfidencePatterns: patterns.length,
      correlationTypes: Object.keys(correlations).length
    };
  }

  shutdown() {
    if (this.captureInterval) {
      clearInterval(this.captureInterval);
      this.captureInterval = null;
    }
    logger.info('Feedback loop engine shutdown');
  }
}

export default new FeedbackLoop();