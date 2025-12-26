import winston from 'winston';
import { performance } from 'perf_hooks';
import { config } from '../../config/rag-config.js';
import suggestionEngine from './suggestion-engine.js';
import anticipationPredictor from './anticipation-predictor.js';
import workflowAutomator from './workflow-automator.js';
import learningFeedback from './learning-feedback.js';
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

class ProactiveMind {
  constructor() {
    this.initialized = false;
    this.activeContext = null;
    this.monitoringInterval = null;
    this.suggestionBuffer = [];
    this.predictionBuffer = [];
    this.metrics = {
      totalInteractions: 0,
      proactiveSuggestions: 0,
      acceptedSuggestions: 0,
      automatedWorkflows: 0,
      avgResponseTime: 0
    };
  }

  async initialize() {
    if (this.initialized) return;
    
    try {
      logger.info('Initializing Proactive Mind...');
      
      // Initialize all components
      await Promise.all([
        suggestionEngine.initialize(),
        anticipationPredictor.initialize(),
        workflowAutomator.initialize(),
        learningFeedback.initialize()
      ]);
      
      // Ensure memory systems are initialized
      await this.ensureMemorySystemsReady();
      
      // Start monitoring
      this.startProactiveMonitoring();
      
      this.initialized = true;
      logger.info('Proactive Mind initialized successfully');
    } catch (error) {
      logger.error('Failed to initialize Proactive Mind', { 
        error: error.message 
      });
      throw error;
    }
  }

  async processInteraction(input, context = {}) {
    const startTime = performance.now();
    this.metrics.totalInteractions++;
    
    try {
      // Update active context
      this.activeContext = {
        ...this.activeContext,
        ...context,
        timestamp: Date.now(),
        input
      };
      
      // Record interaction in episodic memory
      await this.recordInteraction(input, context);
      
      // Generate proactive responses in parallel
      const [
        suggestions,
        predictions,
        automationOpportunities
      ] = await Promise.all([
        this.generateSuggestions(context),
        this.generatePredictions(context),
        this.detectAutomationOpportunities(context)
      ]);
      
      // Combine and rank proactive outputs
      const proactiveResponse = this.combineProactiveOutputs({
        suggestions,
        predictions,
        automationOpportunities
      });
      
      // Track metrics
      const responseTime = performance.now() - startTime;
      this.updateMetrics(proactiveResponse, responseTime);
      
      logger.debug('Proactive interaction processed', {
        suggestionsCount: suggestions.length,
        predictionsCount: predictions.length,
        automationCount: automationOpportunities.length,
        responseTime: `${responseTime.toFixed(2)}ms`
      });
      
      return proactiveResponse;
    } catch (error) {
      logger.error('Failed to process proactive interaction', { 
        error: error.message 
      });
      return this.getEmptyResponse();
    }
  }

  async generateSuggestions(context) {
    try {
      const suggestions = await suggestionEngine.generateSuggestions(context);
      
      // Apply learning adjustments
      const adjustedSuggestions = await Promise.all(
        suggestions.map(async (suggestion) => ({
          ...suggestion,
          confidence: await learningFeedback.getAdjustedConfidence(
            suggestion.type,
            suggestion.action,
            suggestion.confidence
          )
        }))
      );
      
      // Filter and sort
      const filtered = adjustedSuggestions
        .filter(s => s.confidence >= 0.6)
        .sort((a, b) => b.confidence - a.confidence);
      
      this.suggestionBuffer = filtered;
      this.metrics.proactiveSuggestions += filtered.length;
      
      return filtered;
    } catch (error) {
      logger.error('Failed to generate suggestions', { error: error.message });
      return [];
    }
  }

  async generatePredictions(context) {
    try {
      const predictions = await anticipationPredictor.predictNextActions(context);
      
      // Validate predictions against recent patterns
      const validatedPredictions = await this.validatePredictions(predictions, context);
      
      this.predictionBuffer = validatedPredictions;
      
      return validatedPredictions;
    } catch (error) {
      logger.error('Failed to generate predictions', { error: error.message });
      return [];
    }
  }

  async detectAutomationOpportunities(context) {
    try {
      const opportunities = await workflowAutomator.detectRepetitivePatterns(
        context.userId
      );
      
      // Generate automation suggestions
      const automationSuggestions = await Promise.all(
        opportunities.map(async (opportunity) => 
          workflowAutomator.suggestAutomation(opportunity, context)
        )
      );
      
      return automationSuggestions.filter(Boolean);
    } catch (error) {
      logger.error('Failed to detect automation opportunities', { error: error.message });
      return [];
    }
  }

  async recordInteraction(input, context) {
    try {
      const event = {
        type: this.inferInteractionType(input),
        content: input,
        action: this.extractAction(input)
      };
      
      await episodicMemory.recordEpisode(event, context);
      
      // Update semantic clusters if there's an embedding
      if (context.embedding) {
        await semanticClusterer.addMemory({
          content: input,
          embedding: context.embedding,
          metadata: { ...context, timestamp: Date.now() }
        });
      }
    } catch (error) {
      logger.error('Failed to record interaction', { error: error.message });
    }
  }

  async validatePredictions(predictions, context) {
    const validated = [];
    
    for (const prediction of predictions) {
      // Check against recent patterns
      const patternMatch = await this.checkPatternMatch(prediction, context);
      
      if (patternMatch) {
        prediction.confidence *= 1.2; // Boost confidence
      }
      
      // Check against user preferences
      if (context.userId) {
        const userPref = await this.checkUserPreference(prediction, context.userId);
        if (userPref === false) {
          prediction.confidence *= 0.5; // Reduce confidence
        }
      }
      
      validated.push(prediction);
    }
    
    return validated.sort((a, b) => b.confidence - a.confidence);
  }

  async checkPatternMatch(prediction, context) {
    try {
      const recentEpisodes = await episodicMemory.recallEpisodes({
        timeWindow: 'hour',
        limit: 20
      });
      
      const pattern = recentEpisodes
        .map(e => e.event?.action)
        .filter(Boolean)
        .join('->');
      
      return pattern.includes(prediction.action);
    } catch (error) {
      return false;
    }
  }

  async checkUserPreference(prediction, userId) {
    try {
      const userData = await persistentMemory.bootstrapSession(userId);
      
      if (userData.preferences?.disabledActions?.includes(prediction.action)) {
        return false;
      }
      
      if (userData.preferences?.preferredActions?.includes(prediction.action)) {
        return true;
      }
      
      return null;
    } catch (error) {
      return null;
    }
  }

  combineProactiveOutputs({ suggestions, predictions, automationOpportunities }) {
    const combined = {
      suggestions: suggestions.slice(0, 5),
      predictions: predictions.slice(0, 3),
      automations: automationOpportunities.slice(0, 2),
      metadata: {
        timestamp: Date.now(),
        contextId: this.activeContext?.id
      }
    };
    
    // Add priority scores
    combined.priority = this.calculatePriority(combined);
    
    return combined;
  }

  calculatePriority(outputs) {
    let score = 0;
    
    // High-confidence suggestions
    if (outputs.suggestions.some(s => s.confidence > 0.8)) {
      score += 3;
    }
    
    // Immediate predictions
    if (outputs.predictions.some(p => p.timing === 'immediate')) {
      score += 2;
    }
    
    // Automation opportunities
    if (outputs.automations.length > 0) {
      score += 1;
    }
    
    return score;
  }

  async acceptSuggestion(suggestionId) {
    const suggestion = this.suggestionBuffer.find(s => s.id === suggestionId);
    
    if (!suggestion) {
      logger.warn('Suggestion not found', { suggestionId });
      return false;
    }
    
    // Track acceptance
    await Promise.all([
      suggestionEngine.trackAcceptance(suggestionId, true),
      learningFeedback.trackSuggestion(suggestion, true, this.activeContext)
    ]);
    
    // Validate prediction if applicable
    await anticipationPredictor.validatePrediction(suggestion.action);
    
    this.metrics.acceptedSuggestions++;
    
    logger.info('Suggestion accepted', {
      suggestionId,
      action: suggestion.action
    });
    
    return true;
  }

  async rejectSuggestion(suggestionId) {
    const suggestion = this.suggestionBuffer.find(s => s.id === suggestionId);
    
    if (!suggestion) {
      logger.warn('Suggestion not found', { suggestionId });
      return false;
    }
    
    // Track rejection
    await Promise.all([
      suggestionEngine.trackAcceptance(suggestionId, false),
      learningFeedback.trackSuggestion(suggestion, false, this.activeContext)
    ]);
    
    logger.info('Suggestion rejected', {
      suggestionId,
      action: suggestion.action
    });
    
    return true;
  }

  async executeAutomation(automationId) {
    const automation = this.findAutomation(automationId);
    
    if (!automation) {
      logger.warn('Automation not found', { automationId });
      return { success: false, error: 'Automation not found' };
    }
    
    // Create workflow if needed
    if (!automation.workflowId) {
      const workflow = await workflowAutomator.createWorkflow(
        automation.workflow.name,
        automation.workflow.steps,
        this.activeContext
      );
      automation.workflowId = workflow.id;
    }
    
    // Execute workflow
    const result = await workflowAutomator.executeWorkflow(
      automation.workflowId,
      this.activeContext
    );
    
    if (result.success) {
      this.metrics.automatedWorkflows++;
      
      // Track success
      await workflowAutomator.acceptSuggestion(automationId);
    }
    
    return result;
  }

  findAutomation(automationId) {
    // Search in recent automation suggestions
    for (const response of this.suggestionBuffer) {
      if (response.id === automationId) return response;
    }
    return null;
  }

  startProactiveMonitoring() {
    // Monitor for proactive triggers every 30 seconds
    this.monitoringInterval = setInterval(async () => {
      try {
        await this.checkProactiveTriggers();
      } catch (error) {
        logger.error('Proactive monitoring error', { error: error.message });
      }
    }, 30000);
    
    logger.debug('Proactive monitoring started');
  }

  async checkProactiveTriggers() {
    if (!this.activeContext) return;
    
    const timeSinceLastInteraction = Date.now() - this.activeContext.timestamp;
    
    // Check for idle state
    if (timeSinceLastInteraction > 60000) { // 1 minute idle
      await this.handleIdleState();
    }
    
    // Check for scheduled triggers
    await this.checkScheduledTriggers();
    
    // Check for pattern completion
    await this.checkPatternCompletion();
  }

  async handleIdleState() {
    // Generate idle-time suggestions
    const idleSuggestions = await suggestionEngine.generateSuggestions({
      ...this.activeContext,
      idle: true
    });
    
    if (idleSuggestions.length > 0) {
      logger.debug('Generated idle-time suggestions', {
        count: idleSuggestions.length
      });
    }
  }

  async checkScheduledTriggers() {
    const hour = new Date().getHours();
    
    // Morning standup reminder
    if (hour === 9 && !this.activeContext.standupDone) {
      const prediction = {
        action: 'daily_standup',
        type: 'scheduled',
        confidence: 0.9,
        timing: 'immediate'
      };
      
      this.predictionBuffer.push(prediction);
    }
    
    // End of day commit reminder
    if (hour === 17 && !this.activeContext.commitDone) {
      const prediction = {
        action: 'commit_changes',
        type: 'scheduled',
        confidence: 0.8,
        timing: 'immediate'
      };
      
      this.predictionBuffer.push(prediction);
    }
  }

  async checkPatternCompletion() {
    try {
      const recentChain = await episodicMemory.getCausalChain(
        this.activeContext.lastEvent || {}
      );
      
      if (recentChain.length >= 2) {
        // Check if we're in the middle of a known pattern
        const predictions = await anticipationPredictor.predictNextActions({
          ...this.activeContext,
          causalChain: recentChain
        });
        
        if (predictions.length > 0 && predictions[0].confidence > 0.8) {
          logger.debug('Pattern completion detected', {
            nextAction: predictions[0].action
          });
        }
      }
    } catch (error) {
      logger.error('Pattern completion check failed', { error: error.message });
    }
  }

  async ensureMemorySystemsReady() {
    // Initialize memory systems if not already done
    const initPromises = [];
    
    if (!episodicMemory.initialized) {
      initPromises.push(episodicMemory.initialize());
    }
    
    if (!semanticClusterer.initialized) {
      initPromises.push(semanticClusterer.initialize());
    }
    
    if (!persistentMemory.initialized) {
      initPromises.push(persistentMemory.initialize());
    }
    
    if (initPromises.length > 0) {
      await Promise.all(initPromises);
      logger.debug('Memory systems initialized for Proactive Mind');
    }
  }

  inferInteractionType(input) {
    if (typeof input !== 'string') return 'unknown';
    
    const lowercased = input.toLowerCase();
    
    if (lowercased.includes('create')) return 'creation';
    if (lowercased.includes('update') || lowercased.includes('modify')) return 'modification';
    if (lowercased.includes('delete') || lowercased.includes('remove')) return 'deletion';
    if (lowercased.includes('test')) return 'testing';
    if (lowercased.includes('commit')) return 'version_control';
    if (lowercased.includes('?')) return 'query';
    
    return 'general';
  }

  extractAction(input) {
    if (typeof input !== 'string') return 'unknown';
    
    // Extract verb from input
    const words = input.split(' ');
    const verbs = ['create', 'update', 'delete', 'test', 'commit', 'run', 'build', 'deploy'];
    
    for (const word of words) {
      if (verbs.includes(word.toLowerCase())) {
        return word.toLowerCase();
      }
    }
    
    return words[0]?.toLowerCase() || 'unknown';
  }

  updateMetrics(response, responseTime) {
    // Update average response time
    const prevAvg = this.metrics.avgResponseTime;
    const total = this.metrics.totalInteractions;
    this.metrics.avgResponseTime = 
      (prevAvg * (total - 1) + responseTime) / total;
  }

  getEmptyResponse() {
    return {
      suggestions: [],
      predictions: [],
      automations: [],
      metadata: {
        timestamp: Date.now(),
        error: true
      },
      priority: 0
    };
  }

  async getMetrics() {
    const componentMetrics = await Promise.all([
      suggestionEngine.getMetrics(),
      anticipationPredictor.getMetrics(),
      workflowAutomator.getMetrics(),
      learningFeedback.getMetrics()
    ]);
    
    return {
      core: this.metrics,
      suggestionEngine: componentMetrics[0],
      anticipationPredictor: componentMetrics[1],
      workflowAutomator: componentMetrics[2],
      learningFeedback: componentMetrics[3],
      summary: {
        totalInteractions: this.metrics.totalInteractions,
        suggestionAcceptance: `${(componentMetrics[0].acceptanceRate * 100).toFixed(1)}%`,
        predictionAccuracy: `${(componentMetrics[1].accuracy * 100).toFixed(1)}%`,
        automationAcceptance: `${(componentMetrics[2].acceptanceRate * 100).toFixed(1)}%`,
        avgResponseTime: `${this.metrics.avgResponseTime.toFixed(2)}ms`
      }
    };
  }

  async shutdown() {
    if (this.monitoringInterval) {
      clearInterval(this.monitoringInterval);
      this.monitoringInterval = null;
    }
    
    logger.info('Proactive Mind shutdown');
  }
}

export default new ProactiveMind();