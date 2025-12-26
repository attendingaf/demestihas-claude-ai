import winston from 'winston';
import { config } from '../../config/rag-config.js';
import memoryStoreV2 from '../memory/memory-store-v2.js';
import patternDetector from '../patterns/pattern-detector.js';
import sqliteClient from '../core/sqlite-client-optimized.js';

const logger = winston.createLogger({
  level: config.logging.level,
  format: winston.format.json(),
  transports: [
    new winston.transports.Console(),
    new winston.transports.File({ filename: config.logging.file })
  ]
});

class LearningEngine {
  constructor() {
    this.learnedPatterns = new Map();
    this.userBehaviors = new Map();
    this.mistakeCorrections = [];
    this.preferences = {
      commands: new Map(),
      responses: new Map(),
      workflows: new Map()
    };
    this.metrics = {
      patternsLearned: 0,
      mistakesCorrected: 0,
      preferencesAdapted: 0,
      clarificationReduction: 0,
      learningRate: 1.0
    };
    this.learningThresholds = {
      patternConfidence: 0.7,
      behaviorFrequency: 3,
      mistakeThreshold: 2,
      preferenceWeight: 0.8
    };
  }

  async initialize() {
    try {
      // Load existing learned patterns
      await this.loadLearnedPatterns();
      
      // Load user behavior history
      await this.loadUserBehaviors();
      
      // Initialize learning metrics
      await this.initializeMetrics();
      
      logger.info('Learning Engine initialized');
    } catch (error) {
      logger.error('Failed to initialize Learning Engine', { 
        error: error.message 
      });
      throw error;
    }
  }

  async learnFromInteraction(command, response, feedback = null) {
    try {
      // Extract patterns from the interaction
      const patterns = await this.extractPatterns(command, response);
      
      // Learn user preferences
      await this.learnPreferences(command, response, feedback);
      
      // Detect and learn from mistakes
      if (feedback && feedback.corrected) {
        await this.learnFromMistake(command, response, feedback);
      }
      
      // Update behavior model
      await this.updateBehaviorModel(command, response, feedback);
      
      // Adapt future responses
      await this.adaptLearning(patterns);
      
      // Store learning event
      await this.storeLearningEvent(command, response, feedback, patterns);
      
      logger.debug('Learned from interaction', {
        command: command.action,
        patterns: patterns.length,
        feedback: feedback?.type
      });
      
      return {
        patternsLearned: patterns.length,
        adaptations: await this.getAdaptations(command)
      };
    } catch (error) {
      logger.error('Failed to learn from interaction', { 
        error: error.message 
      });
      return { patternsLearned: 0, adaptations: [] };
    }
  }

  async extractPatterns(command, response) {
    const patterns = [];
    
    // Command sequence pattern
    if (command.workflow) {
      const sequencePattern = {
        type: 'workflow',
        name: command.workflow.name,
        steps: command.workflow.steps,
        context: command.context,
        success: response.success,
        confidence: this.calculatePatternConfidence(command, response)
      };
      
      if (sequencePattern.confidence >= this.learningThresholds.patternConfidence) {
        patterns.push(sequencePattern);
        this.learnedPatterns.set(sequencePattern.name, sequencePattern);
      }
    }
    
    // Intent-entity pattern
    if (command.intent && command.entities) {
      const intentPattern = {
        type: 'intent',
        intent: command.intent.type,
        entities: this.generalizeEntities(command.entities),
        response_type: response.type,
        confidence: command.intent.confidence
      };
      
      patterns.push(intentPattern);
    }
    
    // Code generation pattern
    if (response.type === 'code_generation' && response.content.includes('```')) {
      const codePattern = await this.extractCodePattern(response.content);
      if (codePattern) {
        patterns.push(codePattern);
      }
    }
    
    // Error recovery pattern
    if (!response.success && response.recovered) {
      const recoveryPattern = {
        type: 'error_recovery',
        error: response.error,
        recovery_action: response.recovery,
        success: response.recovered
      };
      patterns.push(recoveryPattern);
    }
    
    return patterns;
  }

  async extractCodePattern(content) {
    const codeMatch = content.match(/```(\w+)?\n([\s\S]*?)```/);
    
    if (!codeMatch) return null;
    
    const language = codeMatch[1] || 'unknown';
    const code = codeMatch[2];
    
    // Analyze code structure
    const structure = this.analyzeCodeStructure(code, language);
    
    return {
      type: 'code_generation',
      language,
      structure,
      template: this.extractCodeTemplate(code, structure),
      patterns: this.identifyCodePatterns(code, language)
    };
  }

  analyzeCodeStructure(code, language) {
    const structure = {
      imports: [],
      exports: [],
      functions: [],
      classes: [],
      variables: []
    };
    
    // Simple pattern matching for structure analysis
    const lines = code.split('\n');
    
    for (const line of lines) {
      // Imports
      if (line.match(/^import\s+/)) {
        structure.imports.push(line);
      }
      
      // Exports
      if (line.match(/^export\s+/)) {
        structure.exports.push(line);
      }
      
      // Functions
      const funcMatch = line.match(/(?:function|const|let|var)\s+(\w+)\s*=?\s*(?:\([^)]*\)|async)/);
      if (funcMatch) {
        structure.functions.push(funcMatch[1]);
      }
      
      // Classes
      const classMatch = line.match(/class\s+(\w+)/);
      if (classMatch) {
        structure.classes.push(classMatch[1]);
      }
    }
    
    return structure;
  }

  extractCodeTemplate(code, structure) {
    // Replace specific names with placeholders
    let template = code;
    
    // Replace function names
    for (const func of structure.functions) {
      template = template.replace(new RegExp(func, 'g'), '{functionName}');
    }
    
    // Replace class names
    for (const cls of structure.classes) {
      template = template.replace(new RegExp(cls, 'g'), '{className}');
    }
    
    // Replace string literals with placeholders
    template = template.replace(/'[^']*'/g, "'{string}'");
    template = template.replace(/"[^"]*"/g, '"{string}"');
    
    return template;
  }

  identifyCodePatterns(code, language) {
    const patterns = [];
    
    // Common patterns to identify
    const patternChecks = {
      'async_await': /async[\s\S]*await/,
      'promise': /new Promise|\.then\(|\.catch\(/,
      'arrow_function': /=>\s*{/,
      'destructuring': /const\s*{[^}]+}\s*=/,
      'template_literal': /`[^`]*\${[^}]*}[^`]*`/,
      'try_catch': /try\s*{[\s\S]*}\s*catch/,
      'hooks': /use[A-Z]\w+\(/,
      'jsx': /<[A-Z]\w+/
    };
    
    for (const [name, pattern] of Object.entries(patternChecks)) {
      if (pattern.test(code)) {
        patterns.push(name);
      }
    }
    
    return patterns;
  }

  async learnPreferences(command, response, feedback) {
    const key = `${command.intent?.type}_${command.action}`;
    
    // Learn command preferences
    if (!this.preferences.commands.has(key)) {
      this.preferences.commands.set(key, {
        count: 0,
        variations: [],
        preferred_params: {}
      });
    }
    
    const cmdPref = this.preferences.commands.get(key);
    cmdPref.count++;
    cmdPref.variations.push(command.input);
    
    // Track parameter preferences
    if (command.entities?.parameters) {
      for (const [param, value] of Object.entries(command.entities.parameters)) {
        if (!cmdPref.preferred_params[param]) {
          cmdPref.preferred_params[param] = {};
        }
        cmdPref.preferred_params[param][value] = 
          (cmdPref.preferred_params[param][value] || 0) + 1;
      }
    }
    
    // Learn response preferences
    if (feedback) {
      const responseKey = response.type;
      
      if (!this.preferences.responses.has(responseKey)) {
        this.preferences.responses.set(responseKey, {
          positive: 0,
          negative: 0,
          preferred_style: null
        });
      }
      
      const respPref = this.preferences.responses.get(responseKey);
      
      if (feedback.positive) {
        respPref.positive++;
        
        // Learn preferred response style
        if (response.metadata?.style) {
          respPref.preferred_style = response.metadata.style;
        }
      } else {
        respPref.negative++;
      }
    }
    
    this.metrics.preferencesAdapted++;
  }

  async learnFromMistake(command, response, feedback) {
    const mistake = {
      timestamp: Date.now(),
      command: command.input,
      intent: command.intent,
      incorrect_response: response.content,
      correction: feedback.correction,
      context: feedback.context,
      learned: false
    };
    
    this.mistakeCorrections.push(mistake);
    
    // Analyze the mistake
    const analysis = await this.analyzeMistake(mistake);
    
    if (analysis.pattern) {
      // Store correction pattern
      const correctionPattern = {
        type: 'correction',
        trigger: analysis.trigger,
        incorrect_pattern: analysis.incorrectPattern,
        correct_pattern: analysis.correctPattern,
        confidence: 0.9
      };
      
      this.learnedPatterns.set(
        `correction_${this.mistakeCorrections.length}`,
        correctionPattern
      );
      
      mistake.learned = true;
      this.metrics.mistakesCorrected++;
    }
    
    // Store for future reference
    await memoryStoreV2.storeMemory(JSON.stringify(mistake), {
      type: 'mistake_correction',
      command: command.action,
      learned: mistake.learned
    });
    
    logger.info('Learned from mistake', {
      command: command.action,
      learned: mistake.learned
    });
  }

  async analyzeMistake(mistake) {
    const analysis = {
      pattern: null,
      trigger: null,
      incorrectPattern: null,
      correctPattern: null
    };
    
    // Compare incorrect and correct responses
    if (mistake.correction && mistake.incorrect_response) {
      // Find the key difference
      const diff = this.findDifference(
        mistake.incorrect_response,
        mistake.correction
      );
      
      if (diff) {
        analysis.pattern = 'response_correction';
        analysis.trigger = mistake.intent;
        analysis.incorrectPattern = diff.incorrect;
        analysis.correctPattern = diff.correct;
      }
    }
    
    return analysis;
  }

  findDifference(incorrect, correct) {
    // Simple difference detection
    // In production, use a proper diff algorithm
    
    if (incorrect === correct) return null;
    
    return {
      incorrect: incorrect.substring(0, 100),
      correct: correct.substring(0, 100)
    };
  }

  async updateBehaviorModel(command, response, feedback) {
    const userId = config.user.id || 'default';
    
    if (!this.userBehaviors.has(userId)) {
      this.userBehaviors.set(userId, {
        commandFrequency: new Map(),
        workflowPreferences: new Map(),
        timePatterns: [],
        contextPreferences: new Map(),
        feedbackHistory: []
      });
    }
    
    const behavior = this.userBehaviors.get(userId);
    
    // Update command frequency
    const cmdKey = command.intent?.type || command.action;
    behavior.commandFrequency.set(
      cmdKey,
      (behavior.commandFrequency.get(cmdKey) || 0) + 1
    );
    
    // Track workflow preferences
    if (command.workflow) {
      behavior.workflowPreferences.set(
        command.workflow.name,
        (behavior.workflowPreferences.get(command.workflow.name) || 0) + 1
      );
    }
    
    // Track time patterns
    behavior.timePatterns.push({
      hour: new Date().getHours(),
      day: new Date().getDay(),
      command: cmdKey
    });
    
    // Keep only recent patterns
    if (behavior.timePatterns.length > 1000) {
      behavior.timePatterns = behavior.timePatterns.slice(-500);
    }
    
    // Track context preferences
    if (command.context?.file) {
      const contextKey = command.context.file.split('/').pop();
      behavior.contextPreferences.set(
        contextKey,
        (behavior.contextPreferences.get(contextKey) || 0) + 1
      );
    }
    
    // Store feedback
    if (feedback) {
      behavior.feedbackHistory.push({
        timestamp: Date.now(),
        positive: feedback.positive,
        type: feedback.type
      });
      
      // Keep only recent feedback
      if (behavior.feedbackHistory.length > 100) {
        behavior.feedbackHistory.shift();
      }
    }
  }

  async adaptLearning(patterns) {
    // Adjust learning rate based on pattern success
    const successfulPatterns = patterns.filter(p => p.confidence > 0.8);
    const successRate = patterns.length > 0 ? 
      successfulPatterns.length / patterns.length : 0;
    
    // Adaptive learning rate
    if (successRate > 0.7) {
      this.metrics.learningRate = Math.min(this.metrics.learningRate * 1.1, 2.0);
    } else if (successRate < 0.3) {
      this.metrics.learningRate = Math.max(this.metrics.learningRate * 0.9, 0.5);
    }
    
    // Update pattern confidence thresholds
    if (this.metrics.mistakesCorrected > 10) {
      this.learningThresholds.patternConfidence = Math.min(
        this.learningThresholds.patternConfidence * 1.05,
        0.9
      );
    }
  }

  async getAdaptations(command) {
    const adaptations = [];
    const userId = config.user.id || 'default';
    const behavior = this.userBehaviors.get(userId);
    
    if (!behavior) return adaptations;
    
    // Suggest frequently used commands
    const cmdKey = command.intent?.type || command.action;
    const frequency = behavior.commandFrequency.get(cmdKey) || 0;
    
    if (frequency > this.learningThresholds.behaviorFrequency) {
      // Get preferred parameters
      const cmdPref = this.preferences.commands.get(`${cmdKey}_${command.action}`);
      
      if (cmdPref?.preferred_params) {
        const suggestions = {};
        
        for (const [param, values] of Object.entries(cmdPref.preferred_params)) {
          // Find most frequent value
          const sortedValues = Object.entries(values).sort((a, b) => b[1] - a[1]);
          if (sortedValues.length > 0) {
            suggestions[param] = sortedValues[0][0];
          }
        }
        
        adaptations.push({
          type: 'parameter_suggestion',
          suggestions
        });
      }
    }
    
    // Suggest workflow if applicable
    const workflowSuggestions = [];
    for (const [workflow, count] of behavior.workflowPreferences) {
      if (count > this.learningThresholds.behaviorFrequency) {
        workflowSuggestions.push(workflow);
      }
    }
    
    if (workflowSuggestions.length > 0) {
      adaptations.push({
        type: 'workflow_suggestion',
        workflows: workflowSuggestions
      });
    }
    
    // Apply learned corrections
    const corrections = this.mistakeCorrections.filter(m => 
      m.learned && 
      m.intent === command.intent?.type
    );
    
    if (corrections.length > 0) {
      adaptations.push({
        type: 'correction',
        corrections: corrections.map(c => ({
          avoid: c.incorrect_response,
          prefer: c.correction
        }))
      });
    }
    
    return adaptations;
  }

  calculatePatternConfidence(command, response) {
    let confidence = 0.5;
    
    // Success increases confidence
    if (response.success) confidence += 0.2;
    
    // High intent confidence increases pattern confidence
    if (command.intent?.confidence > 0.8) confidence += 0.1;
    
    // Positive feedback increases confidence
    if (response.feedback?.positive) confidence += 0.2;
    
    return Math.min(confidence, 1.0);
  }

  generalizeEntities(entities) {
    // Generalize entities to create reusable patterns
    const generalized = { ...entities };
    
    if (generalized.target?.name) {
      generalized.target.name = `{${generalized.target.type}}`;
    }
    
    if (generalized.parameters) {
      for (const key of Object.keys(generalized.parameters)) {
        if (typeof generalized.parameters[key] === 'string') {
          generalized.parameters[key] = `{${key}}`;
        }
      }
    }
    
    return generalized;
  }

  async loadLearnedPatterns() {
    try {
      const patterns = await memoryStoreV2.searchMemories('learned pattern', {
        limit: 100,
        filter: { type: 'learned_pattern' }
      });
      
      for (const pattern of patterns) {
        if (pattern.metadata?.pattern) {
          this.learnedPatterns.set(
            pattern.metadata.pattern.name,
            pattern.metadata.pattern
          );
        }
      }
      
      logger.info('Loaded learned patterns', { 
        count: this.learnedPatterns.size 
      });
    } catch (error) {
      logger.error('Failed to load learned patterns', { 
        error: error.message 
      });
    }
  }

  async loadUserBehaviors() {
    try {
      const behaviors = await memoryStoreV2.searchMemories('user behavior', {
        limit: 50,
        filter: { type: 'user_behavior' }
      });
      
      // Reconstruct behavior model from history
      for (const behavior of behaviors) {
        if (behavior.metadata?.userId) {
          const userId = behavior.metadata.userId;
          
          if (!this.userBehaviors.has(userId)) {
            this.userBehaviors.set(userId, behavior.metadata.behavior);
          }
        }
      }
      
      logger.info('Loaded user behaviors', { 
        users: this.userBehaviors.size 
      });
    } catch (error) {
      logger.error('Failed to load user behaviors', { 
        error: error.message 
      });
    }
  }

  async initializeMetrics() {
    // Calculate clarification reduction
    const recentInteractions = await memoryStoreV2.searchMemories('clarification', {
      limit: 100,
      filter: { type: 'interaction' }
    });
    
    if (recentInteractions.length > 20) {
      const recent = recentInteractions.slice(0, 10);
      const older = recentInteractions.slice(-10);
      
      const recentClarifications = recent.filter(i => 
        i.metadata?.required_clarification
      ).length;
      
      const olderClarifications = older.filter(i => 
        i.metadata?.required_clarification
      ).length;
      
      if (olderClarifications > 0) {
        this.metrics.clarificationReduction = 
          ((olderClarifications - recentClarifications) / olderClarifications) * 100;
      }
    }
  }

  async storeLearningEvent(command, response, feedback, patterns) {
    const event = {
      timestamp: Date.now(),
      command: command.action,
      response_type: response.type,
      patterns_learned: patterns.length,
      feedback: feedback?.type,
      adaptations: await this.getAdaptations(command)
    };
    
    await memoryStoreV2.storeMemory(JSON.stringify(event), {
      type: 'learning_event',
      ...event
    });
    
    // Store patterns
    for (const pattern of patterns) {
      await memoryStoreV2.storeMemory(JSON.stringify(pattern), {
        type: 'learned_pattern',
        pattern
      });
    }
    
    this.metrics.patternsLearned += patterns.length;
  }

  async predictNextAction(currentCommand, context) {
    const userId = config.user.id || 'default';
    const behavior = this.userBehaviors.get(userId);
    
    if (!behavior) return null;
    
    const predictions = [];
    
    // Predict based on command frequency
    const frequentCommands = Array.from(behavior.commandFrequency.entries())
      .sort((a, b) => b[1] - a[1])
      .slice(0, 3);
    
    for (const [cmd, freq] of frequentCommands) {
      predictions.push({
        action: cmd,
        confidence: freq / 100,
        reason: 'frequently_used'
      });
    }
    
    // Predict based on workflow patterns
    if (currentCommand.workflow) {
      const currentStep = currentCommand.workflow.currentStep;
      const nextStep = currentCommand.workflow.steps[currentStep + 1];
      
      if (nextStep) {
        predictions.push({
          action: nextStep,
          confidence: 0.8,
          reason: 'workflow_continuation'
        });
      }
    }
    
    // Predict based on time patterns
    const currentHour = new Date().getHours();
    const timePatterns = behavior.timePatterns.filter(p => 
      Math.abs(p.hour - currentHour) <= 1
    );
    
    if (timePatterns.length > 0) {
      const timeCommands = {};
      
      for (const pattern of timePatterns) {
        timeCommands[pattern.command] = (timeCommands[pattern.command] || 0) + 1;
      }
      
      const sortedTimeCommands = Object.entries(timeCommands)
        .sort((a, b) => b[1] - a[1]);
      
      if (sortedTimeCommands.length > 0) {
        predictions.push({
          action: sortedTimeCommands[0][0],
          confidence: sortedTimeCommands[0][1] / timePatterns.length,
          reason: 'time_pattern'
        });
      }
    }
    
    // Sort by confidence
    predictions.sort((a, b) => b.confidence - a.confidence);
    
    return predictions.length > 0 ? predictions[0] : null;
  }

  getMetrics() {
    const avgRelevance = this.metrics.patternsLearned > 0 ?
      this.metrics.mistakesCorrected / this.metrics.patternsLearned :
      0;
    
    return {
      ...this.metrics,
      improvementRate: avgRelevance,
      learnedPatterns: this.learnedPatterns.size,
      userBehaviors: this.userBehaviors.size,
      mistakeCorrections: this.mistakeCorrections.length,
      clarificationReduction: `${this.metrics.clarificationReduction.toFixed(1)}%`
    };
  }

  reset() {
    this.learnedPatterns.clear();
    this.userBehaviors.clear();
    this.mistakeCorrections = [];
    this.preferences = {
      commands: new Map(),
      responses: new Map(),
      workflows: new Map()
    };
    
    logger.info('Learning Engine reset');
  }
}

export default new LearningEngine();