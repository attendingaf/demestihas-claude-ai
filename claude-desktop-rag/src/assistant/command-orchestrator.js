import winston from 'winston';
import { performance } from 'perf_hooks';
import { config } from '../../config/rag-config.js';
import memoryStoreV2 from '../memory/memory-store-v2.js';
import contextPrioritizer from '../context/context-prioritizer.js';
import performanceMonitor from '../monitoring/performance-monitor.js';

const logger = winston.createLogger({
  level: config.logging.level,
  format: winston.format.json(),
  transports: [
    new winston.transports.Console(),
    new winston.transports.File({ filename: config.logging.file })
  ]
});

// Command patterns and intents
const COMMAND_PATTERNS = {
  // Code operations
  CREATE: /^(create|make|generate|build|add|new)\s+(.+)/i,
  MODIFY: /^(modify|change|update|edit|refactor|fix|improve)\s+(.+)/i,
  DELETE: /^(delete|remove|clean|clear)\s+(.+)/i,
  SEARCH: /^(find|search|locate|look for|where is|show)\s+(.+)/i,
  
  // Analysis operations
  EXPLAIN: /^(explain|describe|what is|how does|tell me about)\s+(.+)/i,
  ANALYZE: /^(analyze|review|check|inspect|audit)\s+(.+)/i,
  SUGGEST: /^(suggest|recommend|propose|what should)\s+(.+)/i,
  
  // Project operations
  SETUP: /^(setup|initialize|configure|install)\s+(.+)/i,
  TEST: /^(test|run tests|check tests|verify)\s+(.+)/i,
  BUILD: /^(build|compile|bundle|package)\s+(.+)/i,
  DEPLOY: /^(deploy|publish|release|ship)\s+(.+)/i,
  
  // Navigation
  GOTO: /^(go to|open|navigate to|show me)\s+(.+)/i,
  LIST: /^(list|show all|display|get)\s+(.+)/i,
  
  // Help
  HELP: /^(help|how do I|how to|what can you)\s*(.+)?/i,
  
  // Context operations
  CONTEXT: /^(set context|working on|currently in|focus on)\s+(.+)/i,
  REMEMBER: /^(remember|note|keep in mind|store)\s+(.+)/i
};

// Intent categories
const INTENT_CATEGORIES = {
  CODE_GENERATION: ['CREATE', 'MODIFY', 'DELETE'],
  CODE_ANALYSIS: ['EXPLAIN', 'ANALYZE', 'SUGGEST'],
  PROJECT_MANAGEMENT: ['SETUP', 'TEST', 'BUILD', 'DEPLOY'],
  NAVIGATION: ['GOTO', 'LIST', 'SEARCH'],
  ASSISTANCE: ['HELP'],
  CONTEXT_MANAGEMENT: ['CONTEXT', 'REMEMBER']
};

class CommandOrchestrator {
  constructor() {
    this.commandHistory = [];
    this.activeWorkflows = new Map();
    this.intentCache = new Map();
    this.metrics = {
      totalCommands: 0,
      avgProcessingTime: 0,
      intentAccuracy: 0,
      commandDistribution: {}
    };
  }

  async initialize() {
    try {
      // Initialize memory store for context
      await memoryStoreV2.initialize();
      
      logger.info('Command Orchestrator initialized');
    } catch (error) {
      logger.error('Failed to initialize Command Orchestrator', { 
        error: error.message 
      });
      throw error;
    }
  }

  async processCommand(input, context = {}) {
    const startTime = performance.now();
    
    try {
      // Parse and recognize intent
      const intent = await this.recognizeIntent(input);
      
      // Extract entities and parameters
      const entities = await this.extractEntities(input, intent);
      
      // Check for multi-step workflow
      const workflow = this.identifyWorkflow(intent, entities);
      
      // Route to appropriate handler
      const result = await this.routeCommand(intent, entities, workflow, context);
      
      // Track metrics
      const processingTime = performance.now() - startTime;
      this.trackMetrics(intent, processingTime);
      performanceMonitor.trackRetrievalTime(processingTime, 'command');
      
      // Store command history
      this.addToHistory(input, intent, result, processingTime);
      
      logger.debug('Command processed', {
        intent: intent.type,
        time: processingTime,
        success: result.success
      });
      
      return result;
    } catch (error) {
      logger.error('Failed to process command', { 
        input,
        error: error.message 
      });
      
      return {
        success: false,
        error: error.message,
        suggestion: await this.getSuggestion(input)
      };
    }
  }

  async recognizeIntent(input) {
    const normalizedInput = input.trim().toLowerCase();
    
    // Check cache first
    if (this.intentCache.has(normalizedInput)) {
      return this.intentCache.get(normalizedInput);
    }
    
    // Pattern matching
    for (const [intentType, pattern] of Object.entries(COMMAND_PATTERNS)) {
      const match = input.match(pattern);
      if (match) {
        const intent = {
          type: intentType,
          confidence: 1.0,
          match: match[0],
          captured: match[2] || '',
          category: this.getIntentCategory(intentType)
        };
        
        // Cache the intent
        this.intentCache.set(normalizedInput, intent);
        
        return intent;
      }
    }
    
    // Fallback to semantic understanding
    return await this.semanticIntentRecognition(input);
  }

  async semanticIntentRecognition(input) {
    // Use embeddings to find similar commands
    const results = await memoryStoreV2.searchMemories(input, {
      limit: 5,
      filter: { type: 'command' }
    });
    
    if (results.length > 0 && results[0].similarity > 0.8) {
      const previousCommand = results[0];
      
      if (previousCommand.metadata && previousCommand.metadata.intent) {
        return {
          type: previousCommand.metadata.intent,
          confidence: results[0].similarity,
          match: input,
          captured: input,
          category: this.getIntentCategory(previousCommand.metadata.intent),
          semantic: true
        };
      }
    }
    
    // Default to search if unclear
    return {
      type: 'SEARCH',
      confidence: 0.5,
      match: input,
      captured: input,
      category: 'NAVIGATION',
      fallback: true
    };
  }

  async extractEntities(input, intent) {
    const entities = {
      target: null,
      action: null,
      parameters: {},
      modifiers: [],
      references: []
    };
    
    // Extract based on intent type
    switch (intent.type) {
      case 'CREATE':
        entities.action = 'create';
        entities.target = this.extractTarget(intent.captured);
        entities.parameters = this.extractCreateParameters(intent.captured);
        break;
        
      case 'MODIFY':
        entities.action = 'modify';
        entities.target = this.extractTarget(intent.captured);
        entities.parameters = this.extractModifyParameters(intent.captured);
        break;
        
      case 'SEARCH':
        entities.action = 'search';
        entities.target = intent.captured;
        entities.parameters = this.extractSearchParameters(input);
        break;
        
      case 'EXPLAIN':
        entities.action = 'explain';
        entities.target = intent.captured;
        entities.parameters.depth = this.extractExplanationDepth(input);
        break;
        
      case 'TEST':
        entities.action = 'test';
        entities.target = intent.captured || 'all';
        entities.parameters = this.extractTestParameters(input);
        break;
        
      default:
        entities.target = intent.captured;
        entities.action = intent.type.toLowerCase();
    }
    
    // Extract references ("it", "that", "the function")
    entities.references = await this.resolveReferences(input);
    
    return entities;
  }

  extractTarget(captured) {
    // Extract file names, function names, class names, etc.
    const patterns = {
      file: /(\w+\.\w+)/,
      function: /function\s+(\w+)|(\w+)\s+function/i,
      class: /class\s+(\w+)|(\w+)\s+class/i,
      component: /component\s+(\w+)|(\w+)\s+component/i,
      module: /module\s+(\w+)|(\w+)\s+module/i
    };
    
    for (const [type, pattern] of Object.entries(patterns)) {
      const match = captured.match(pattern);
      if (match) {
        return {
          type,
          name: match[1] || match[2],
          raw: captured
        };
      }
    }
    
    return {
      type: 'generic',
      name: captured,
      raw: captured
    };
  }

  extractCreateParameters(captured) {
    const params = {};
    
    // Extract template/type
    if (captured.includes('react')) params.template = 'react';
    if (captured.includes('vue')) params.template = 'vue';
    if (captured.includes('typescript')) params.language = 'typescript';
    if (captured.includes('test')) params.type = 'test';
    if (captured.includes('component')) params.type = 'component';
    if (captured.includes('api')) params.type = 'api';
    
    // Extract name
    const nameMatch = captured.match(/called\s+(\w+)|named\s+(\w+)/i);
    if (nameMatch) {
      params.name = nameMatch[1] || nameMatch[2];
    }
    
    return params;
  }

  extractModifyParameters(captured) {
    const params = {};
    
    // Extract modification type
    if (captured.includes('refactor')) params.modificationType = 'refactor';
    if (captured.includes('optimize')) params.modificationType = 'optimize';
    if (captured.includes('fix')) params.modificationType = 'fix';
    if (captured.includes('improve')) params.modificationType = 'improve';
    if (captured.includes('rename')) params.modificationType = 'rename';
    
    // Extract scope
    if (captured.includes('all')) params.scope = 'all';
    if (captured.includes('function')) params.scope = 'function';
    if (captured.includes('class')) params.scope = 'class';
    if (captured.includes('file')) params.scope = 'file';
    
    return params;
  }

  extractSearchParameters(input) {
    const params = {};
    
    // Extract search scope
    if (input.includes('in file')) params.scope = 'file';
    if (input.includes('in project')) params.scope = 'project';
    if (input.includes('in folder')) params.scope = 'folder';
    
    // Extract search type
    if (input.includes('function')) params.type = 'function';
    if (input.includes('class')) params.type = 'class';
    if (input.includes('variable')) params.type = 'variable';
    if (input.includes('import')) params.type = 'import';
    
    return params;
  }

  extractExplanationDepth(input) {
    if (input.includes('detail') || input.includes('comprehensive')) {
      return 'detailed';
    }
    if (input.includes('brief') || input.includes('summary')) {
      return 'brief';
    }
    if (input.includes('beginner') || input.includes('simple')) {
      return 'beginner';
    }
    return 'standard';
  }

  extractTestParameters(input) {
    const params = {};
    
    if (input.includes('unit')) params.type = 'unit';
    if (input.includes('integration')) params.type = 'integration';
    if (input.includes('e2e') || input.includes('end-to-end')) params.type = 'e2e';
    if (input.includes('coverage')) params.coverage = true;
    if (input.includes('watch')) params.watch = true;
    
    return params;
  }

  async resolveReferences(input) {
    const references = [];
    
    // Pronouns and references
    const referencePatterns = [
      { pattern: /\bit\b/g, type: 'pronoun' },
      { pattern: /\bthat\b/g, type: 'demonstrative' },
      { pattern: /\bthis\b/g, type: 'demonstrative' },
      { pattern: /\bthe (\w+)\b/g, type: 'definite' },
      { pattern: /\babove\b/g, type: 'positional' },
      { pattern: /\bprevious\b/g, type: 'temporal' },
      { pattern: /\blast\b/g, type: 'temporal' }
    ];
    
    for (const { pattern, type } of referencePatterns) {
      let match;
      while ((match = pattern.exec(input)) !== null) {
        references.push({
          text: match[0],
          type,
          position: match.index,
          resolved: null // Will be resolved by conversation manager
        });
      }
    }
    
    return references;
  }

  identifyWorkflow(intent, entities) {
    // Identify multi-step workflows
    const workflows = {
      'CREATE_COMPONENT': {
        steps: ['create_file', 'add_boilerplate', 'create_test', 'update_exports'],
        triggers: ['CREATE', 'component']
      },
      'REFACTOR_CODE': {
        steps: ['analyze_code', 'identify_improvements', 'apply_changes', 'run_tests'],
        triggers: ['MODIFY', 'refactor']
      },
      'ADD_FEATURE': {
        steps: ['create_branch', 'implement_feature', 'write_tests', 'update_docs'],
        triggers: ['CREATE', 'feature']
      },
      'FIX_BUG': {
        steps: ['reproduce_issue', 'locate_cause', 'implement_fix', 'verify_fix'],
        triggers: ['MODIFY', 'fix']
      },
      'DEPLOY_APP': {
        steps: ['run_tests', 'build_app', 'deploy', 'verify_deployment'],
        triggers: ['DEPLOY']
      }
    };
    
    for (const [name, workflow] of Object.entries(workflows)) {
      const matchesIntent = workflow.triggers.includes(intent.type);
      const matchesEntity = workflow.triggers.some(trigger => 
        entities.target?.name?.includes(trigger) ||
        entities.action?.includes(trigger)
      );
      
      if (matchesIntent || matchesEntity) {
        return {
          name,
          steps: workflow.steps,
          currentStep: 0,
          context: { intent, entities }
        };
      }
    }
    
    return null;
  }

  async routeCommand(intent, entities, workflow, context) {
    const router = {
      // Code operations
      'CREATE': this.handleCreate.bind(this),
      'MODIFY': this.handleModify.bind(this),
      'DELETE': this.handleDelete.bind(this),
      'SEARCH': this.handleSearch.bind(this),
      
      // Analysis operations
      'EXPLAIN': this.handleExplain.bind(this),
      'ANALYZE': this.handleAnalyze.bind(this),
      'SUGGEST': this.handleSuggest.bind(this),
      
      // Project operations
      'SETUP': this.handleSetup.bind(this),
      'TEST': this.handleTest.bind(this),
      'BUILD': this.handleBuild.bind(this),
      'DEPLOY': this.handleDeploy.bind(this),
      
      // Navigation
      'GOTO': this.handleGoto.bind(this),
      'LIST': this.handleList.bind(this),
      
      // Help
      'HELP': this.handleHelp.bind(this),
      
      // Context
      'CONTEXT': this.handleContext.bind(this),
      'REMEMBER': this.handleRemember.bind(this)
    };
    
    const handler = router[intent.type];
    
    if (!handler) {
      throw new Error(`No handler for intent type: ${intent.type}`);
    }
    
    // Handle workflow if present
    if (workflow) {
      return await this.executeWorkflow(workflow, handler, entities, context);
    }
    
    // Direct execution
    return await handler(entities, context);
  }

  async executeWorkflow(workflow, handler, entities, context) {
    const workflowId = `${workflow.name}_${Date.now()}`;
    
    this.activeWorkflows.set(workflowId, {
      ...workflow,
      status: 'active',
      startTime: Date.now()
    });
    
    const results = {
      workflowId,
      name: workflow.name,
      steps: [],
      success: true
    };
    
    try {
      for (let i = 0; i < workflow.steps.length; i++) {
        const step = workflow.steps[i];
        
        logger.debug('Executing workflow step', {
          workflow: workflow.name,
          step,
          progress: `${i + 1}/${workflow.steps.length}`
        });
        
        // Execute step (simplified - would be more complex in production)
        const stepResult = await handler(entities, {
          ...context,
          workflowStep: step,
          workflowContext: workflow.context
        });
        
        results.steps.push({
          name: step,
          result: stepResult,
          success: stepResult.success
        });
        
        if (!stepResult.success && !stepResult.optional) {
          results.success = false;
          break;
        }
        
        // Update workflow state
        const activeWorkflow = this.activeWorkflows.get(workflowId);
        activeWorkflow.currentStep = i + 1;
      }
    } finally {
      // Clean up
      this.activeWorkflows.delete(workflowId);
    }
    
    return results;
  }

  // Command handlers
  async handleCreate(entities, context) {
    return {
      success: true,
      action: 'create',
      target: entities.target,
      parameters: entities.parameters,
      message: `Creating ${entities.target.name}`,
      requiresConfirmation: true
    };
  }

  async handleModify(entities, context) {
    return {
      success: true,
      action: 'modify',
      target: entities.target,
      parameters: entities.parameters,
      message: `Modifying ${entities.target.name}`,
      requiresConfirmation: true
    };
  }

  async handleDelete(entities, context) {
    return {
      success: true,
      action: 'delete',
      target: entities.target,
      message: `Deleting ${entities.target.name}`,
      requiresConfirmation: true,
      warning: 'This action cannot be undone'
    };
  }

  async handleSearch(entities, context) {
    // Use memory store for search
    const results = await memoryStoreV2.searchMemories(entities.target, {
      limit: 10,
      ...entities.parameters
    });
    
    return {
      success: true,
      action: 'search',
      query: entities.target,
      results: results.map(r => ({
        content: r.content,
        similarity: r.similarity,
        metadata: r.metadata
      })),
      count: results.length
    };
  }

  async handleExplain(entities, context) {
    return {
      success: true,
      action: 'explain',
      target: entities.target,
      depth: entities.parameters.depth,
      message: `Explaining ${entities.target}`
    };
  }

  async handleAnalyze(entities, context) {
    return {
      success: true,
      action: 'analyze',
      target: entities.target,
      message: `Analyzing ${entities.target}`
    };
  }

  async handleSuggest(entities, context) {
    return {
      success: true,
      action: 'suggest',
      target: entities.target,
      message: `Generating suggestions for ${entities.target}`
    };
  }

  async handleSetup(entities, context) {
    return {
      success: true,
      action: 'setup',
      target: entities.target,
      message: `Setting up ${entities.target}`
    };
  }

  async handleTest(entities, context) {
    return {
      success: true,
      action: 'test',
      target: entities.target,
      parameters: entities.parameters,
      message: `Running tests for ${entities.target}`
    };
  }

  async handleBuild(entities, context) {
    return {
      success: true,
      action: 'build',
      target: entities.target,
      message: `Building ${entities.target}`
    };
  }

  async handleDeploy(entities, context) {
    return {
      success: true,
      action: 'deploy',
      target: entities.target,
      message: `Deploying ${entities.target}`,
      requiresConfirmation: true
    };
  }

  async handleGoto(entities, context) {
    return {
      success: true,
      action: 'navigate',
      target: entities.target,
      message: `Navigating to ${entities.target.name}`
    };
  }

  async handleList(entities, context) {
    return {
      success: true,
      action: 'list',
      target: entities.target,
      message: `Listing ${entities.target}`
    };
  }

  async handleHelp(entities, context) {
    const helpTopics = {
      commands: Object.keys(COMMAND_PATTERNS),
      categories: Object.keys(INTENT_CATEGORIES),
      workflows: ['CREATE_COMPONENT', 'REFACTOR_CODE', 'ADD_FEATURE', 'FIX_BUG']
    };
    
    return {
      success: true,
      action: 'help',
      topics: helpTopics,
      message: 'Available commands and features'
    };
  }

  async handleContext(entities, context) {
    // Set current context
    if (entities.target) {
      await contextPrioritizer.setCurrentContext(
        entities.target.name,
        entities.parameters.function
      );
    }
    
    return {
      success: true,
      action: 'context',
      target: entities.target,
      message: `Context set to ${entities.target.name}`
    };
  }

  async handleRemember(entities, context) {
    // Store in memory
    await memoryStoreV2.storeMemory(entities.target, {
      type: 'user_note',
      intent: 'REMEMBER',
      ...entities.parameters
    });
    
    return {
      success: true,
      action: 'remember',
      content: entities.target,
      message: 'Noted and stored in memory'
    };
  }

  async getSuggestion(input) {
    // Find similar successful commands
    const similar = await memoryStoreV2.searchMemories(input, {
      limit: 3,
      filter: { success: true }
    });
    
    if (similar.length > 0) {
      return {
        message: 'Did you mean:',
        suggestions: similar.map(s => s.content)
      };
    }
    
    return {
      message: 'Try commands like:',
      suggestions: [
        'create a new React component',
        'explain this function',
        'find all TODO comments',
        'run tests for this file'
      ]
    };
  }

  getIntentCategory(intentType) {
    for (const [category, intents] of Object.entries(INTENT_CATEGORIES)) {
      if (intents.includes(intentType)) {
        return category;
      }
    }
    return 'UNKNOWN';
  }

  addToHistory(input, intent, result, processingTime) {
    const entry = {
      timestamp: Date.now(),
      input,
      intent: intent.type,
      confidence: intent.confidence,
      success: result.success,
      processingTime,
      result: result.action
    };
    
    this.commandHistory.push(entry);
    
    // Keep only last 100 commands
    if (this.commandHistory.length > 100) {
      this.commandHistory.shift();
    }
    
    // Store successful commands for learning
    if (result.success) {
      memoryStoreV2.storeMemory(input, {
        type: 'command',
        intent: intent.type,
        entities: result.target,
        success: true,
        processingTime
      });
    }
  }

  trackMetrics(intent, processingTime) {
    this.metrics.totalCommands++;
    
    // Update average processing time
    const prevAvg = this.metrics.avgProcessingTime;
    this.metrics.avgProcessingTime = 
      (prevAvg * (this.metrics.totalCommands - 1) + processingTime) / 
      this.metrics.totalCommands;
    
    // Track command distribution
    if (!this.metrics.commandDistribution[intent.type]) {
      this.metrics.commandDistribution[intent.type] = 0;
    }
    this.metrics.commandDistribution[intent.type]++;
    
    // Calculate intent accuracy (based on confidence)
    if (intent.confidence) {
      const prevAccuracy = this.metrics.intentAccuracy;
      this.metrics.intentAccuracy = 
        (prevAccuracy * (this.metrics.totalCommands - 1) + intent.confidence) / 
        this.metrics.totalCommands;
    }
  }

  getMetrics() {
    return {
      ...this.metrics,
      recentCommands: this.commandHistory.slice(-10),
      activeWorkflows: this.activeWorkflows.size,
      cacheSize: this.intentCache.size
    };
  }

  clearCache() {
    this.intentCache.clear();
    logger.debug('Intent cache cleared');
  }
}

export default new CommandOrchestrator();