import winston from 'winston';
import { performance } from 'perf_hooks';
import { config } from '../../config/rag-config.js';
import episodicMemory from '../memory/advanced/episodic-memory.js';
import persistentMemory from '../memory/advanced/persistent-memory.js';

const logger = winston.createLogger({
  level: config.logging.level,
  format: winston.format.json(),
  transports: [
    new winston.transports.Console(),
    new winston.transports.File({ filename: config.logging.file })
  ]
});

class AnticipationPredictor {
  constructor() {
    this.predictions = new Map();
    this.userModels = new Map();
    this.preloadQueue = [];
    this.confidenceThreshold = 0.7;
    this.predictionWindow = 3; // Predict next 3 actions
    this.modelUpdateInterval = 5 * 60 * 1000; // 5 minutes
    this.lastModelUpdate = 0;
    this.metrics = {
      totalPredictions: 0,
      correctPredictions: 0,
      preloadHits: 0,
      preloadMisses: 0,
      avgPredictionTime: 0
    };
  }

  async initialize() {
    logger.info('Initializing anticipation predictor...');
    await this.loadUserModels();
    this.startModelUpdates();
    logger.info('Anticipation predictor initialized');
  }

  async predictNextActions(currentContext) {
    const startTime = performance.now();
    
    try {
      // Get user model
      const userModel = await this.getUserModel(currentContext.userId);
      
      // Get recent episode chain
      const causalChain = await this.getRecentCausalChain(currentContext);
      
      // Generate predictions using multiple strategies
      const [
        sequencePredictions,
        temporalPredictions,
        contextualPredictions,
        behaviorPredictions
      ] = await Promise.all([
        this.predictFromSequence(causalChain, userModel),
        this.predictFromTemporal(currentContext),
        this.predictFromContext(currentContext, userModel),
        this.predictFromBehavior(userModel, currentContext)
      ]);
      
      // Combine and rank predictions
      const allPredictions = this.combinePredictions([
        ...sequencePredictions,
        ...temporalPredictions,
        ...contextualPredictions,
        ...behaviorPredictions
      ]);
      
      // Filter and limit predictions
      const finalPredictions = allPredictions
        .filter(p => p.confidence >= this.confidenceThreshold)
        .sort((a, b) => b.confidence - a.confidence)
        .slice(0, this.predictionWindow);
      
      // Trigger preloading for high-confidence predictions
      await this.triggerPreloading(finalPredictions);
      
      // Store predictions for validation
      this.storePredictions(finalPredictions, currentContext);
      
      // Update metrics
      const predictionTime = performance.now() - startTime;
      this.updateMetrics(finalPredictions, predictionTime);
      
      logger.debug('Generated predictions', {
        count: finalPredictions.length,
        time: `${predictionTime.toFixed(2)}ms`
      });
      
      return finalPredictions;
    } catch (error) {
      logger.error('Failed to predict next actions', { error: error.message });
      return [];
    }
  }

  async predictFromSequence(causalChain, userModel) {
    const predictions = [];
    
    if (!causalChain || causalChain.length < 2) {
      return predictions;
    }
    
    // Extract action sequence
    const sequence = causalChain.map(e => e.event?.type || e.event?.action).filter(Boolean);
    
    // Look for matching patterns in user model
    if (userModel.sequences) {
      for (const [pattern, data] of userModel.sequences) {
        if (this.sequenceMatches(sequence, pattern)) {
          const nextActions = this.extractNextFromPattern(pattern, sequence);
          
          for (const action of nextActions) {
            predictions.push({
              action,
              type: 'sequence',
              confidence: data.confidence * (data.frequency / 100),
              timing: data.avgTiming,
              metadata: {
                pattern,
                frequency: data.frequency,
                source: 'sequence_analysis'
              }
            });
          }
        }
      }
    }
    
    return predictions;
  }

  async predictFromTemporal(context) {
    const predictions = [];
    
    const now = new Date();
    const hour = now.getHours();
    const day = now.getDay();
    
    // Time-based predictions
    const timePatterns = {
      morning: { hours: [8, 9, 10], actions: ['check_emails', 'review_tasks', 'standup'] },
      lunch: { hours: [12, 13], actions: ['break', 'review_progress'] },
      evening: { hours: [17, 18], actions: ['commit_changes', 'update_tasks', 'plan_tomorrow'] }
    };
    
    for (const [period, data] of Object.entries(timePatterns)) {
      if (data.hours.includes(hour)) {
        for (const action of data.actions) {
          predictions.push({
            action,
            type: 'temporal',
            confidence: 0.6,
            timing: 'immediate',
            metadata: {
              period,
              trigger: 'time_of_day'
            }
          });
        }
      }
    }
    
    // Day-based predictions
    if (day === 1) { // Monday
      predictions.push({
        action: 'weekly_planning',
        type: 'temporal',
        confidence: 0.7,
        timing: 'immediate',
        metadata: { trigger: 'start_of_week' }
      });
    }
    
    if (day === 5) { // Friday
      predictions.push({
        action: 'weekly_review',
        type: 'temporal',
        confidence: 0.7,
        timing: 'end_of_day',
        metadata: { trigger: 'end_of_week' }
      });
    }
    
    return predictions;
  }

  async predictFromContext(context, userModel) {
    const predictions = [];
    
    // Error context predictions
    if (context.error) {
      predictions.push({
        action: 'debug',
        type: 'contextual',
        confidence: 0.9,
        timing: 'immediate',
        metadata: { trigger: 'error_detected' }
      });
      
      predictions.push({
        action: 'search_solution',
        type: 'contextual',
        confidence: 0.8,
        timing: 'next',
        metadata: { trigger: 'error_recovery' }
      });
    }
    
    // Code context predictions
    if (context.codeFile) {
      const extension = context.codeFile.split('.').pop();
      
      if (extension === 'test.js' || extension === 'spec.js') {
        predictions.push({
          action: 'run_tests',
          type: 'contextual',
          confidence: 0.85,
          timing: 'after_save',
          metadata: { trigger: 'test_file_edited' }
        });
      }
      
      if (userModel.preferences?.autoFormat) {
        predictions.push({
          action: 'format_code',
          type: 'contextual',
          confidence: 0.75,
          timing: 'before_save',
          metadata: { trigger: 'code_editing' }
        });
      }
    }
    
    // Project context predictions
    if (context.projectId && userModel.projectPatterns) {
      const projectPatterns = userModel.projectPatterns[context.projectId];
      if (projectPatterns) {
        for (const pattern of projectPatterns) {
          predictions.push({
            action: pattern.action,
            type: 'contextual',
            confidence: pattern.confidence,
            timing: pattern.timing,
            metadata: {
              projectId: context.projectId,
              pattern: pattern.name
            }
          });
        }
      }
    }
    
    return predictions;
  }

  async predictFromBehavior(userModel, context) {
    const predictions = [];
    
    if (!userModel.behaviors) {
      return predictions;
    }
    
    // Workflow predictions
    if (userModel.behaviors.workflows) {
      for (const workflow of userModel.behaviors.workflows) {
        if (this.workflowApplies(workflow, context)) {
          const nextStep = this.getNextWorkflowStep(workflow, context);
          if (nextStep) {
            predictions.push({
              action: nextStep.action,
              type: 'behavioral',
              confidence: workflow.confidence * 0.9,
              timing: nextStep.timing || 'next',
              metadata: {
                workflow: workflow.name,
                step: nextStep.index
              }
            });
          }
        }
      }
    }
    
    // Habit predictions
    if (userModel.behaviors.habits) {
      for (const habit of userModel.behaviors.habits) {
        if (this.shouldTriggerHabit(habit, context)) {
          predictions.push({
            action: habit.action,
            type: 'behavioral',
            confidence: habit.strength,
            timing: 'periodic',
            metadata: {
              habit: habit.name,
              frequency: habit.frequency
            }
          });
        }
      }
    }
    
    return predictions;
  }

  async getUserModel(userId) {
    if (!userId) {
      return this.getDefaultModel();
    }
    
    // Check if model needs update
    if (Date.now() - this.lastModelUpdate > this.modelUpdateInterval) {
      await this.updateUserModel(userId);
    }
    
    let model = this.userModels.get(userId);
    if (!model) {
      model = await this.buildUserModel(userId);
      this.userModels.set(userId, model);
    }
    
    return model;
  }

  async buildUserModel(userId) {
    const model = {
      userId,
      sequences: new Map(),
      behaviors: {
        workflows: [],
        habits: []
      },
      projectPatterns: {},
      preferences: {},
      lastUpdated: Date.now()
    };
    
    try {
      // Load from persistent memory
      const userData = await persistentMemory.bootstrapSession(userId);
      
      // Extract sequences from patterns
      if (userData.patterns) {
        for (const pattern of userData.patterns) {
          const sequence = pattern.pattern.split('->');
          model.sequences.set(pattern.pattern, {
            frequency: pattern.frequency,
            confidence: Math.min(pattern.frequency / 10, 1.0),
            avgTiming: 1000 // Default 1 second
          });
        }
      }
      
      // Set preferences
      model.preferences = userData.preferences || {};
      
      // Extract behaviors from facts
      if (userData.facts) {
        model.behaviors = this.extractBehaviors(userData.facts);
      }
      
    } catch (error) {
      logger.error('Failed to build user model', { userId, error: error.message });
    }
    
    return model;
  }

  extractBehaviors(facts) {
    const behaviors = {
      workflows: [],
      habits: []
    };
    
    // Simple extraction - in production, use ML
    for (const fact of facts) {
      if (fact.content.includes('workflow')) {
        behaviors.workflows.push({
          name: fact.content,
          confidence: fact.confidence,
          steps: []
        });
      }
      
      if (fact.content.includes('always') || fact.content.includes('usually')) {
        behaviors.habits.push({
          name: fact.content,
          action: this.extractActionFromFact(fact.content),
          strength: fact.confidence,
          frequency: 'frequent'
        });
      }
    }
    
    return behaviors;
  }

  extractActionFromFact(fact) {
    // Simple extraction
    const verbs = ['creates', 'runs', 'checks', 'updates', 'reviews'];
    for (const verb of verbs) {
      if (fact.includes(verb)) {
        const after = fact.split(verb)[1];
        return after ? after.trim().split(' ')[0] : verb;
      }
    }
    return 'unknown_action';
  }

  async getRecentCausalChain(context) {
    try {
      const recentEpisodes = await episodicMemory.recallEpisodes({
        timeWindow: 'recent',
        limit: 10
      });
      
      if (recentEpisodes.length > 0) {
        return await episodicMemory.getCausalChain(recentEpisodes[0].event);
      }
    } catch (error) {
      logger.error('Failed to get causal chain', { error: error.message });
    }
    
    return [];
  }

  sequenceMatches(current, pattern) {
    const patternArray = typeof pattern === 'string' ? pattern.split('->') : pattern;
    
    // Check if current sequence is a prefix of pattern
    if (current.length >= patternArray.length) return false;
    
    for (let i = 0; i < current.length; i++) {
      if (current[i] !== patternArray[i]) return false;
    }
    
    return true;
  }

  extractNextFromPattern(pattern, currentSequence) {
    const patternArray = typeof pattern === 'string' ? pattern.split('->') : pattern;
    const nextIndex = currentSequence.length;
    
    if (nextIndex < patternArray.length) {
      return patternArray.slice(nextIndex, Math.min(nextIndex + this.predictionWindow, patternArray.length));
    }
    
    return [];
  }

  workflowApplies(workflow, context) {
    // Check if workflow conditions are met
    if (workflow.trigger === 'always') return true;
    if (workflow.trigger === 'error' && context.error) return true;
    if (workflow.trigger === 'file_type' && context.codeFile?.includes(workflow.filePattern)) return true;
    
    return false;
  }

  getNextWorkflowStep(workflow, context) {
    // Find current step and return next
    if (!workflow.steps || workflow.steps.length === 0) return null;
    
    // For now, return first step
    return {
      ...workflow.steps[0],
      index: 0
    };
  }

  shouldTriggerHabit(habit, context) {
    // Check if habit should be triggered
    const now = Date.now();
    
    if (habit.lastTriggered && now - habit.lastTriggered < 60 * 60 * 1000) {
      return false; // Don't trigger more than once per hour
    }
    
    if (habit.context && !this.contextMatches(habit.context, context)) {
      return false;
    }
    
    return true;
  }

  contextMatches(requiredContext, currentContext) {
    for (const [key, value] of Object.entries(requiredContext)) {
      if (currentContext[key] !== value) return false;
    }
    return true;
  }

  combinePredictions(predictions) {
    const combined = new Map();
    
    for (const prediction of predictions) {
      const key = prediction.action;
      
      if (combined.has(key)) {
        // Combine confidence scores
        const existing = combined.get(key);
        existing.confidence = Math.max(existing.confidence, prediction.confidence);
        
        // Combine metadata
        existing.sources = existing.sources || [];
        existing.sources.push(prediction.type);
      } else {
        combined.set(key, {
          ...prediction,
          sources: [prediction.type]
        });
      }
    }
    
    return Array.from(combined.values());
  }

  async triggerPreloading(predictions) {
    const highConfidence = predictions.filter(p => p.confidence > 0.8);
    
    for (const prediction of highConfidence) {
      if (prediction.timing === 'immediate' || prediction.timing === 'next') {
        await this.preloadResources(prediction);
      }
    }
  }

  async preloadResources(prediction) {
    logger.debug('Preloading resources for prediction', {
      action: prediction.action,
      confidence: prediction.confidence
    });
    
    // Add to preload queue
    this.preloadQueue.push({
      prediction,
      timestamp: Date.now(),
      status: 'pending'
    });
    
    // In production, actually preload relevant data/resources
    // For now, just track it
    this.metrics.preloadHits++;
  }

  storePredictions(predictions, context) {
    const id = `pred_${Date.now()}_${Math.random().toString(36).substr(2, 9)}`;
    
    this.predictions.set(id, {
      predictions,
      context,
      timestamp: Date.now(),
      validated: false
    });
    
    // Clean old predictions
    this.cleanOldPredictions();
  }

  cleanOldPredictions() {
    const cutoff = Date.now() - 60 * 60 * 1000; // 1 hour
    
    for (const [id, data] of this.predictions.entries()) {
      if (data.timestamp < cutoff) {
        this.predictions.delete(id);
      }
    }
  }

  async validatePrediction(actualAction) {
    // Check if any recent predictions matched
    for (const [id, data] of this.predictions.entries()) {
      if (!data.validated && Date.now() - data.timestamp < 60000) {
        const matched = data.predictions.find(p => p.action === actualAction);
        
        if (matched) {
          this.metrics.correctPredictions++;
          data.validated = true;
          
          logger.debug('Prediction validated', {
            action: actualAction,
            confidence: matched.confidence,
            type: matched.type
          });
          
          return true;
        }
      }
    }
    
    return false;
  }

  async updateUserModel(userId) {
    const model = await this.buildUserModel(userId);
    this.userModels.set(userId, model);
    this.lastModelUpdate = Date.now();
    
    logger.debug('Updated user model', { userId });
  }

  async loadUserModels() {
    // Load frequently active user models
    logger.debug('Loading user models for anticipation');
  }

  startModelUpdates() {
    setInterval(() => {
      this.cleanOldPredictions();
      
      // Update active user models
      for (const userId of this.userModels.keys()) {
        this.updateUserModel(userId).catch(error => {
          logger.error('Failed to update user model', { userId, error: error.message });
        });
      }
    }, this.modelUpdateInterval);
  }

  getDefaultModel() {
    return {
      sequences: new Map(),
      behaviors: { workflows: [], habits: [] },
      projectPatterns: {},
      preferences: {},
      lastUpdated: Date.now()
    };
  }

  updateMetrics(predictions, predictionTime) {
    this.metrics.totalPredictions += predictions.length;
    
    // Update average prediction time
    const prevAvg = this.metrics.avgPredictionTime;
    const total = this.metrics.totalPredictions;
    this.metrics.avgPredictionTime = 
      (prevAvg * (total - predictions.length) + predictionTime) / total;
  }

  async getMetrics() {
    const accuracy = this.metrics.totalPredictions > 0
      ? this.metrics.correctPredictions / this.metrics.totalPredictions
      : 0;
    
    const preloadEfficiency = (this.metrics.preloadHits + this.metrics.preloadMisses) > 0
      ? this.metrics.preloadHits / (this.metrics.preloadHits + this.metrics.preloadMisses)
      : 0;
    
    return {
      ...this.metrics,
      accuracy,
      preloadEfficiency,
      activeModels: this.userModels.size,
      queuedPreloads: this.preloadQueue.length
    };
  }
}

export default new AnticipationPredictor();