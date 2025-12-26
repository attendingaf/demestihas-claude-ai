import winston from 'winston';
import { performance } from 'perf_hooks';
import { config } from '../../config/rag-config.js';
import commandOrchestrator from './command-orchestrator.js';
import responseGenerator from './response-generator.js';
import learningEngine from './learning-engine.js';
import conversationManager from './conversation-manager.js';
import codeIntelligence from './code-intelligence.js';
import performanceMonitor from '../monitoring/performance-monitor.js';

const logger = winston.createLogger({
  level: config.logging.level,
  format: winston.format.json(),
  transports: [
    new winston.transports.Console(),
    new winston.transports.File({ filename: config.logging.file })
  ]
});

class AssistantCore {
  constructor() {
    this.initialized = false;
    this.activeConversation = null;
    this.metrics = {
      totalInteractions: 0,
      avgResponseTime: 0,
      successRate: 0,
      userSatisfaction: 0
    };
  }

  async initialize() {
    if (this.initialized) return;
    
    try {
      logger.info('Initializing Assistant Core...');
      
      // Initialize all components
      await Promise.all([
        commandOrchestrator.initialize(),
        responseGenerator.initialize(),
        learningEngine.initialize(),
        conversationManager.initialize(),
        codeIntelligence.initialize()
      ]);
      
      this.initialized = true;
      logger.info('Assistant Core initialized successfully');
    } catch (error) {
      logger.error('Failed to initialize Assistant Core', { 
        error: error.message 
      });
      throw error;
    }
  }

  async processInput(input, context = {}) {
    await this.ensureInitialized();
    const startTime = performance.now();
    
    try {
      // Start or continue conversation
      if (!this.activeConversation) {
        this.activeConversation = await conversationManager.startConversation(context);
      }
      
      // Process command
      const commandResult = await commandOrchestrator.processCommand(input, context);
      
      // Handle code-related commands
      if (this.isCodeRelated(commandResult)) {
        commandResult.codeAnalysis = await this.analyzeCodeContext(commandResult, context);
      }
      
      // Generate response
      const response = await responseGenerator.generateResponse(commandResult, context);
      
      // Add to conversation
      await conversationManager.addTurn(input, response, this.activeConversation);
      
      // Learn from interaction
      const learningResult = await learningEngine.learnFromInteraction(
        { input, intent: commandResult.intent, ...commandResult },
        response
      );
      
      // Track performance
      const responseTime = performance.now() - startTime;
      this.trackMetrics(commandResult, response, responseTime);
      performanceMonitor.trackRetrievalTime(responseTime, 'assistant');
      
      // Build final response
      const finalResponse = {
        ...response,
        commandResult,
        conversationId: this.activeConversation,
        learningApplied: learningResult.patternsLearned > 0,
        responseTime,
        metrics: {
          processingTime: responseTime,
          confidence: response.confidence,
          contextUsed: !!context
        }
      };
      
      logger.debug('Input processed', {
        responseTime,
        success: commandResult.success,
        learningApplied: finalResponse.learningApplied
      });
      
      return finalResponse;
    } catch (error) {
      logger.error('Failed to process input', { 
        input,
        error: error.message 
      });
      
      return this.generateErrorResponse(error, input);
    }
  }

  async processConversation(messages, context = {}) {
    await this.ensureInitialized();
    
    const responses = [];
    const conversationId = await conversationManager.startConversation(context);
    
    for (const message of messages) {
      const response = await this.processInput(message, {
        ...context,
        conversationId
      });
      
      responses.push(response);
      
      // Apply learning between turns
      if (responses.length > 1) {
        const previousResponse = responses[responses.length - 2];
        await learningEngine.learnFromInteraction(
          { input: message },
          response,
          { previousContext: previousResponse }
        );
      }
    }
    
    return {
      conversationId,
      responses,
      summary: this.summarizeConversation(responses)
    };
  }

  isCodeRelated(commandResult) {
    const codeActions = ['create', 'modify', 'analyze', 'refactor', 'test'];
    return codeActions.includes(commandResult.action) ||
           commandResult.target?.type === 'function' ||
           commandResult.target?.type === 'class' ||
           commandResult.target?.type === 'component';
  }

  async analyzeCodeContext(commandResult, context) {
    if (!commandResult.codeContent && !context.currentCode) {
      return null;
    }
    
    const code = commandResult.codeContent || context.currentCode;
    const language = context.language || 'javascript';
    
    try {
      const analysis = await codeIntelligence.analyzeCode(code, language);
      
      // Apply modifications if requested
      if (commandResult.action === 'modify' && commandResult.modifications) {
        const modified = await codeIntelligence.modifyCode(
          code,
          commandResult.modifications,
          language
        );
        
        return {
          ...analysis,
          modified
        };
      }
      
      // Generate refactoring suggestions if requested
      if (commandResult.action === 'refactor' || commandResult.action === 'analyze') {
        const suggestions = await codeIntelligence.suggestRefactoring(code, language);
        
        return {
          ...analysis,
          refactoringSuggestions: suggestions
        };
      }
      
      return analysis;
    } catch (error) {
      logger.error('Code analysis failed', { error: error.message });
      return null;
    }
  }

  async provideFeedback(responseId, feedback) {
    // Process user feedback
    const response = await this.getResponse(responseId);
    
    if (!response) {
      throw new Error('Response not found');
    }
    
    // Learn from feedback
    await learningEngine.learnFromInteraction(
      response.commandResult,
      response,
      feedback
    );
    
    // Update preferences if needed
    if (feedback.preferences) {
      responseGenerator.updatePreferences(feedback.preferences);
    }
    
    logger.info('Feedback processed', {
      responseId,
      type: feedback.type,
      positive: feedback.positive
    });
    
    return {
      acknowledged: true,
      learningApplied: true
    };
  }

  async getConversationHistory(conversationId = null) {
    return conversationManager.getConversationHistory(
      conversationId || this.activeConversation
    );
  }

  async predictNextAction(currentContext) {
    return learningEngine.predictNextAction(
      currentContext.lastCommand,
      currentContext
    );
  }

  summarizeConversation(responses) {
    const summary = {
      totalTurns: responses.length,
      successfulActions: responses.filter(r => r.commandResult?.success).length,
      topics: [],
      avgResponseTime: 0,
      avgConfidence: 0
    };
    
    // Extract topics
    const topics = new Set();
    for (const response of responses) {
      if (response.commandResult?.action) {
        topics.add(response.commandResult.action);
      }
    }
    summary.topics = Array.from(topics);
    
    // Calculate averages
    const times = responses.map(r => r.responseTime || 0);
    const confidences = responses.map(r => r.confidence || 0);
    
    summary.avgResponseTime = times.reduce((a, b) => a + b, 0) / times.length;
    summary.avgConfidence = confidences.reduce((a, b) => a + b, 0) / confidences.length;
    
    return summary;
  }

  generateErrorResponse(error, input) {
    return {
      content: `I encountered an error: ${error.message}. Please try rephrasing your request.`,
      type: 'error',
      confidence: 1.0,
      commandResult: {
        success: false,
        error: error.message,
        input
      },
      metadata: {
        timestamp: Date.now(),
        error: error.stack
      }
    };
  }

  async getResponse(responseId) {
    // In production, this would retrieve from storage
    // For now, return a mock response
    return {
      id: responseId,
      commandResult: {},
      content: ''
    };
  }

  trackMetrics(commandResult, response, responseTime) {
    this.metrics.totalInteractions++;
    
    // Update average response time
    const prevAvg = this.metrics.avgResponseTime;
    this.metrics.avgResponseTime = 
      (prevAvg * (this.metrics.totalInteractions - 1) + responseTime) / 
      this.metrics.totalInteractions;
    
    // Update success rate
    if (commandResult.success) {
      const prevSuccesses = this.metrics.successRate * (this.metrics.totalInteractions - 1);
      this.metrics.successRate = (prevSuccesses + 1) / this.metrics.totalInteractions;
    } else {
      const prevSuccesses = this.metrics.successRate * (this.metrics.totalInteractions - 1);
      this.metrics.successRate = prevSuccesses / this.metrics.totalInteractions;
    }
    
    // Estimate user satisfaction based on response confidence
    const prevSatisfaction = this.metrics.userSatisfaction * (this.metrics.totalInteractions - 1);
    this.metrics.userSatisfaction = 
      (prevSatisfaction + response.confidence) / this.metrics.totalInteractions;
  }

  async ensureInitialized() {
    if (!this.initialized) {
      await this.initialize();
    }
  }

  async getMetrics() {
    const componentMetrics = await Promise.all([
      commandOrchestrator.getMetrics(),
      responseGenerator.getMetrics(),
      learningEngine.getMetrics(),
      conversationManager.getMetrics(),
      codeIntelligence.getMetrics()
    ]);
    
    return {
      core: this.metrics,
      commandOrchestrator: componentMetrics[0],
      responseGenerator: componentMetrics[1],
      learningEngine: componentMetrics[2],
      conversationManager: componentMetrics[3],
      codeIntelligence: componentMetrics[4],
      summary: {
        totalInteractions: this.metrics.totalInteractions,
        avgResponseTime: `${this.metrics.avgResponseTime.toFixed(2)}ms`,
        successRate: `${(this.metrics.successRate * 100).toFixed(1)}%`,
        userSatisfaction: `${(this.metrics.userSatisfaction * 100).toFixed(1)}%`,
        learningEffectiveness: `${componentMetrics[2].clarificationReduction}`,
        activeConversations: componentMetrics[3].activeConversations
      }
    };
  }

  async reset() {
    // Reset all components
    commandOrchestrator.clearCache();
    learningEngine.reset();
    
    // End active conversation
    if (this.activeConversation) {
      conversationManager.endConversation(this.activeConversation);
      this.activeConversation = null;
    }
    
    logger.info('Assistant Core reset');
  }
}

export default new AssistantCore();