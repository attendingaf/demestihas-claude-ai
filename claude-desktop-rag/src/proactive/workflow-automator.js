import winston from 'winston';
import { v4 as uuidv4 } from 'uuid';
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

class WorkflowAutomator {
  constructor() {
    this.workflows = new Map();
    this.templates = new Map();
    this.activeAutomations = new Map();
    this.patternThreshold = 3; // Min occurrences to suggest automation
    this.confidenceThreshold = 0.75;
    this.maxWorkflowSteps = 10;
    this.metrics = {
      totalWorkflows: 0,
      automatedWorkflows: 0,
      timeSaved: 0,
      suggestionsAccepted: 0,
      suggestionsRejected: 0
    };
  }

  async initialize() {
    logger.info('Initializing workflow automator...');
    await this.loadWorkflowTemplates();
    await this.detectExistingPatterns();
    logger.info('Workflow automator initialized');
  }

  async detectRepetitivePatterns(userId) {
    try {
      // Get user's episodic memories
      const episodes = await episodicMemory.recallEpisodes({
        timeWindow: 'week',
        limit: 100
      });
      
      // Get user patterns from persistent memory
      const userData = await persistentMemory.bootstrapSession(userId);
      const userPatterns = userData.patterns || [];
      
      // Analyze for repetitive sequences
      const sequences = this.extractSequences(episodes);
      const repetitivePatterns = this.identifyRepetitions(sequences, userPatterns);
      
      // Generate automation opportunities
      const opportunities = [];
      
      for (const pattern of repetitivePatterns) {
        if (pattern.occurrences >= this.patternThreshold) {
          const opportunity = await this.createAutomationOpportunity(pattern, userId);
          if (opportunity) {
            opportunities.push(opportunity);
          }
        }
      }
      
      logger.info('Detected automation opportunities', {
        count: opportunities.length,
        userId
      });
      
      return opportunities;
    } catch (error) {
      logger.error('Failed to detect patterns', { error: error.message });
      return [];
    }
  }

  async suggestAutomation(pattern, context) {
    const suggestion = {
      id: uuidv4(),
      type: 'workflow_automation',
      pattern: pattern.sequence,
      occurrences: pattern.occurrences,
      confidence: this.calculateAutomationConfidence(pattern),
      workflow: await this.generateWorkflow(pattern, context),
      benefits: this.calculateBenefits(pattern),
      timestamp: Date.now()
    };
    
    if (suggestion.confidence >= this.confidenceThreshold) {
      logger.debug('Suggesting automation', {
        pattern: pattern.sequence,
        confidence: suggestion.confidence
      });
      
      return suggestion;
    }
    
    return null;
  }

  async createWorkflow(name, steps, context = {}) {
    const workflowId = uuidv4();
    
    const workflow = {
      id: workflowId,
      name,
      steps: this.validateSteps(steps),
      context,
      created: Date.now(),
      lastExecuted: null,
      executionCount: 0,
      averageTime: 0,
      enabled: true
    };
    
    this.workflows.set(workflowId, workflow);
    this.metrics.totalWorkflows++;
    
    logger.info('Workflow created', {
      id: workflowId,
      name,
      steps: workflow.steps.length
    });
    
    return workflow;
  }

  async executeWorkflow(workflowId, inputContext = {}) {
    const workflow = this.workflows.get(workflowId);
    
    if (!workflow || !workflow.enabled) {
      logger.warn('Workflow not found or disabled', { workflowId });
      return { success: false, error: 'Workflow not available' };
    }
    
    const executionId = uuidv4();
    const startTime = Date.now();
    
    // Create automation context
    const automation = {
      id: executionId,
      workflowId,
      status: 'running',
      currentStep: 0,
      context: { ...workflow.context, ...inputContext },
      results: [],
      startTime
    };
    
    this.activeAutomations.set(executionId, automation);
    
    try {
      // Execute steps sequentially
      for (let i = 0; i < workflow.steps.length; i++) {
        const step = workflow.steps[i];
        automation.currentStep = i;
        
        const stepResult = await this.executeStep(step, automation.context);
        automation.results.push(stepResult);
        
        if (!stepResult.success && step.required) {
          throw new Error(`Step ${i} failed: ${stepResult.error}`);
        }
        
        // Update context with step results
        if (stepResult.output) {
          automation.context[`step${i}_output`] = stepResult.output;
        }
      }
      
      // Update workflow metrics
      const executionTime = Date.now() - startTime;
      workflow.lastExecuted = Date.now();
      workflow.executionCount++;
      workflow.averageTime = 
        (workflow.averageTime * (workflow.executionCount - 1) + executionTime) / 
        workflow.executionCount;
      
      automation.status = 'completed';
      automation.endTime = Date.now();
      
      this.metrics.automatedWorkflows++;
      this.metrics.timeSaved += executionTime;
      
      logger.info('Workflow executed successfully', {
        workflowId,
        executionId,
        time: `${executionTime}ms`
      });
      
      return {
        success: true,
        executionId,
        results: automation.results,
        executionTime
      };
    } catch (error) {
      automation.status = 'failed';
      automation.error = error.message;
      
      logger.error('Workflow execution failed', {
        workflowId,
        executionId,
        error: error.message
      });
      
      return {
        success: false,
        executionId,
        error: error.message
      };
    } finally {
      // Clean up after delay
      setTimeout(() => {
        this.activeAutomations.delete(executionId);
      }, 60000); // Keep for 1 minute for debugging
    }
  }

  async preFillWorkflow(templateId, context) {
    const template = this.templates.get(templateId);
    
    if (!template) {
      logger.warn('Template not found', { templateId });
      return null;
    }
    
    // Pre-fill based on context and history
    const preFilled = {
      ...template,
      fields: {}
    };
    
    // Use context to pre-fill fields
    for (const field of template.fields) {
      if (context[field.name]) {
        preFilled.fields[field.name] = context[field.name];
      } else if (field.default) {
        preFilled.fields[field.name] = field.default;
      } else {
        // Try to predict from history
        preFilled.fields[field.name] = await this.predictFieldValue(field, context);
      }
    }
    
    logger.debug('Pre-filled workflow', {
      templateId,
      filledFields: Object.keys(preFilled.fields).length
    });
    
    return preFilled;
  }

  extractSequences(episodes) {
    const sequences = [];
    const windowSize = 5; // Look for sequences up to 5 steps
    
    for (let i = 0; i < episodes.length - 1; i++) {
      for (let len = 2; len <= Math.min(windowSize, episodes.length - i); len++) {
        const sequence = episodes
          .slice(i, i + len)
          .map(e => this.getActionIdentifier(e))
          .join('->');
        
        sequences.push({
          sequence,
          startIndex: i,
          length: len,
          episodes: episodes.slice(i, i + len)
        });
      }
    }
    
    return sequences;
  }

  identifyRepetitions(sequences, userPatterns) {
    const patternCounts = new Map();
    
    // Count sequence occurrences
    for (const seq of sequences) {
      const count = patternCounts.get(seq.sequence) || { 
        sequence: seq.sequence, 
        occurrences: 0, 
        instances: [] 
      };
      
      count.occurrences++;
      count.instances.push(seq);
      patternCounts.set(seq.sequence, count);
    }
    
    // Add user patterns
    for (const pattern of userPatterns) {
      if (patternCounts.has(pattern.pattern)) {
        const count = patternCounts.get(pattern.pattern);
        count.occurrences += pattern.frequency;
        count.fromHistory = true;
      }
    }
    
    // Filter repetitive patterns
    const repetitive = [];
    for (const pattern of patternCounts.values()) {
      if (pattern.occurrences >= 2) {
        repetitive.push(pattern);
      }
    }
    
    // Sort by occurrence count
    repetitive.sort((a, b) => b.occurrences - a.occurrences);
    
    return repetitive;
  }

  getActionIdentifier(episode) {
    if (episode.event) {
      return episode.event.type || episode.event.action || 'unknown';
    }
    return 'unknown';
  }

  async createAutomationOpportunity(pattern, userId) {
    const steps = pattern.sequence.split('->');
    
    if (steps.length > this.maxWorkflowSteps) {
      return null; // Too complex
    }
    
    return {
      id: uuidv4(),
      pattern: pattern.sequence,
      occurrences: pattern.occurrences,
      suggestedName: this.generateWorkflowName(steps),
      steps: steps.map((step, index) => ({
        action: step,
        order: index,
        required: true,
        params: {}
      })),
      estimatedTimeSaved: steps.length * 1000, // 1 second per step estimate
      confidence: this.calculateAutomationConfidence(pattern),
      userId
    };
  }

  generateWorkflowName(steps) {
    // Generate descriptive name from steps
    const actions = steps.slice(0, 3).join('_');
    return `auto_${actions}_workflow`;
  }

  calculateAutomationConfidence(pattern) {
    let confidence = 0.5; // Base confidence
    
    // Increase based on occurrences
    confidence += Math.min(pattern.occurrences / 10, 0.3);
    
    // Increase if from history
    if (pattern.fromHistory) {
      confidence += 0.1;
    }
    
    // Increase for shorter patterns (more likely to be intentional)
    const steps = pattern.sequence.split('->').length;
    if (steps <= 3) {
      confidence += 0.1;
    }
    
    return Math.min(confidence, 1.0);
  }

  async generateWorkflow(pattern, context) {
    const steps = pattern.sequence.split('->').map((action, index) => ({
      id: `step_${index}`,
      action,
      type: this.inferStepType(action),
      params: this.inferStepParams(action, context),
      required: true,
      order: index
    }));
    
    return {
      name: this.generateWorkflowName(steps.map(s => s.action)),
      description: `Automated workflow based on ${pattern.occurrences} occurrences`,
      steps,
      triggers: this.inferTriggers(pattern, context),
      conditions: this.inferConditions(pattern, context)
    };
  }

  inferStepType(action) {
    const typeMap = {
      create: 'creation',
      update: 'modification',
      delete: 'deletion',
      test: 'validation',
      commit: 'version_control',
      search: 'query',
      analyze: 'analysis'
    };
    
    for (const [key, type] of Object.entries(typeMap)) {
      if (action.toLowerCase().includes(key)) {
        return type;
      }
    }
    
    return 'generic';
  }

  inferStepParams(action, context) {
    const params = {};
    
    // Extract parameters based on action type
    if (action.includes('file')) {
      params.target = 'file';
      params.path = context.currentFile || null;
    }
    
    if (action.includes('test')) {
      params.type = 'test';
      params.framework = context.testFramework || 'jest';
    }
    
    return params;
  }

  inferTriggers(pattern, context) {
    const triggers = [];
    
    // Time-based triggers
    if (pattern.instances && pattern.instances.length > 0) {
      const times = pattern.instances.map(i => new Date(i.startTime).getHours());
      const avgHour = Math.round(times.reduce((a, b) => a + b, 0) / times.length);
      
      if (times.every(h => Math.abs(h - avgHour) <= 1)) {
        triggers.push({
          type: 'scheduled',
          schedule: `daily_at_${avgHour}:00`
        });
      }
    }
    
    // Event-based triggers
    if (pattern.sequence.includes('error')) {
      triggers.push({
        type: 'event',
        event: 'error_detected'
      });
    }
    
    if (pattern.sequence.includes('save')) {
      triggers.push({
        type: 'event',
        event: 'file_saved'
      });
    }
    
    return triggers;
  }

  inferConditions(pattern, context) {
    const conditions = [];
    
    // Project-specific conditions
    if (context.projectId) {
      conditions.push({
        type: 'context',
        field: 'projectId',
        value: context.projectId
      });
    }
    
    // File type conditions
    if (pattern.sequence.includes('test')) {
      conditions.push({
        type: 'file',
        pattern: '*.test.js'
      });
    }
    
    return conditions;
  }

  calculateBenefits(pattern) {
    const steps = pattern.sequence.split('->').length;
    
    return {
      timeSaved: `${steps} seconds per execution`,
      reducedErrors: 'Consistent execution reduces mistakes',
      productivity: `${pattern.occurrences * steps} seconds saved so far`
    };
  }

  validateSteps(steps) {
    return steps.map((step, index) => ({
      ...step,
      id: step.id || `step_${index}`,
      order: step.order || index,
      required: step.required !== false,
      retries: step.retries || 0,
      timeout: step.timeout || 5000
    }));
  }

  async executeStep(step, context) {
    logger.debug('Executing workflow step', {
      id: step.id,
      action: step.action
    });
    
    try {
      // Simulate step execution - in production, integrate with actual actions
      const result = await this.simulateStepExecution(step, context);
      
      return {
        success: true,
        stepId: step.id,
        output: result,
        executionTime: Math.random() * 1000 // Simulated time
      };
    } catch (error) {
      return {
        success: false,
        stepId: step.id,
        error: error.message
      };
    }
  }

  async simulateStepExecution(step, context) {
    // Simulate different step types
    switch (step.type) {
      case 'creation':
        return { created: `${step.action}_${Date.now()}` };
      
      case 'modification':
        return { modified: true, target: step.params.target };
      
      case 'validation':
        return { valid: true, tests: 10, passed: 10 };
      
      case 'query':
        return { results: [], count: 0 };
      
      default:
        return { executed: true };
    }
  }

  async predictFieldValue(field, context) {
    // Simple prediction based on field type and context
    if (field.type === 'string' && field.name.includes('name')) {
      return context.projectName || 'default';
    }
    
    if (field.type === 'boolean') {
      return true;
    }
    
    if (field.type === 'number') {
      return field.min || 0;
    }
    
    return null;
  }

  async loadWorkflowTemplates() {
    // Load common workflow templates
    const templates = [
      {
        id: 'test_and_commit',
        name: 'Test and Commit',
        fields: [
          { name: 'commitMessage', type: 'string', required: true },
          { name: 'runTests', type: 'boolean', default: true }
        ],
        steps: [
          { action: 'run_tests', type: 'validation' },
          { action: 'stage_changes', type: 'version_control' },
          { action: 'commit', type: 'version_control' }
        ]
      },
      {
        id: 'create_component',
        name: 'Create Component',
        fields: [
          { name: 'componentName', type: 'string', required: true },
          { name: 'includeTests', type: 'boolean', default: true }
        ],
        steps: [
          { action: 'create_file', type: 'creation' },
          { action: 'add_boilerplate', type: 'modification' },
          { action: 'create_test_file', type: 'creation', required: false }
        ]
      }
    ];
    
    for (const template of templates) {
      this.templates.set(template.id, template);
    }
    
    logger.debug(`Loaded ${templates.length} workflow templates`);
  }

  async detectExistingPatterns() {
    // Detect patterns on initialization
    try {
      const recentEpisodes = await episodicMemory.recallEpisodes({
        timeWindow: 'day',
        limit: 50
      });
      
      const sequences = this.extractSequences(recentEpisodes);
      const patterns = this.identifyRepetitions(sequences, []);
      
      logger.debug(`Detected ${patterns.length} existing patterns`);
    } catch (error) {
      logger.error('Failed to detect existing patterns', { error: error.message });
    }
  }

  async acceptSuggestion(suggestionId) {
    this.metrics.suggestionsAccepted++;
    logger.info('Automation suggestion accepted', { suggestionId });
  }

  async rejectSuggestion(suggestionId) {
    this.metrics.suggestionsRejected++;
    logger.info('Automation suggestion rejected', { suggestionId });
  }

  async getMetrics() {
    const acceptanceRate = (this.metrics.suggestionsAccepted + this.metrics.suggestionsRejected) > 0
      ? this.metrics.suggestionsAccepted / (this.metrics.suggestionsAccepted + this.metrics.suggestionsRejected)
      : 0;
    
    return {
      ...this.metrics,
      acceptanceRate,
      activeWorkflows: this.workflows.size,
      activeAutomations: this.activeAutomations.size,
      avgTimeSaved: this.metrics.automatedWorkflows > 0
        ? this.metrics.timeSaved / this.metrics.automatedWorkflows
        : 0
    };
  }
}

export default new WorkflowAutomator();