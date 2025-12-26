import winston from 'winston';
import { config } from '../../config/rag-config.js';
import memoryStoreV2 from '../memory/memory-store-v2.js';
import projectContextManager from '../context/project-context-manager.js';
import patternDetector from '../patterns/pattern-detector.js';

const logger = winston.createLogger({
  level: config.logging.level,
  format: winston.format.json(),
  transports: [
    new winston.transports.Console(),
    new winston.transports.File({ filename: config.logging.file })
  ]
});

// Response templates for different contexts
const RESPONSE_TEMPLATES = {
  code_generation: {
    brief: '```{language}\n{code}\n```',
    standard: 'Here\'s the {type} you requested:\n\n```{language}\n{code}\n```\n\n{explanation}',
    detailed: '## {title}\n\n{description}\n\n### Implementation\n\n```{language}\n{code}\n```\n\n### Explanation\n\n{explanation}\n\n### Usage\n\n{usage}\n\n### Notes\n\n{notes}'
  },
  
  explanation: {
    brief: '{summary}',
    standard: '**{topic}**\n\n{explanation}\n\n{example}',
    detailed: '# {topic}\n\n## Overview\n\n{overview}\n\n## Detailed Explanation\n\n{explanation}\n\n## Examples\n\n{examples}\n\n## Related Concepts\n\n{related}\n\n## Best Practices\n\n{practices}'
  },
  
  error: {
    brief: '❌ {error}',
    standard: '**Error:** {error}\n\n**Suggestion:** {suggestion}',
    detailed: '## Error Encountered\n\n{error}\n\n### Possible Causes\n\n{causes}\n\n### Suggested Solutions\n\n{solutions}\n\n### Prevention\n\n{prevention}'
  },
  
  success: {
    brief: '✅ {message}',
    standard: '**Success:** {message}\n\n{details}',
    detailed: '## Operation Completed\n\n{message}\n\n### Details\n\n{details}\n\n### Next Steps\n\n{nextSteps}'
  },
  
  analysis: {
    brief: '{summary}',
    standard: '**Analysis Results**\n\n{findings}\n\n**Recommendations:** {recommendations}',
    detailed: '# Code Analysis Report\n\n## Summary\n\n{summary}\n\n## Findings\n\n{findings}\n\n## Metrics\n\n{metrics}\n\n## Recommendations\n\n{recommendations}\n\n## Action Items\n\n{actions}'
  }
};

// Code snippets for common patterns
const CODE_PATTERNS = {
  react_component: {
    functional: `const {name} = ({props}) => {
  return (
    <div className="{className}">
      {content}
    </div>
  );
};

export default {name};`,
    
    class: `import React, { Component } from 'react';

class {name} extends Component {
  constructor(props) {
    super(props);
    this.state = {
      {state}
    };
  }

  render() {
    return (
      <div className="{className}">
        {content}
      </div>
    );
  }
}

export default {name};`
  },
  
  test: {
    unit: `describe('{name}', () => {
  it('{testCase}', () => {
    {testBody}
  });
});`,
    
    integration: `describe('{feature}', () => {
  beforeEach(() => {
    {setup}
  });

  it('{scenario}', async () => {
    {testSteps}
  });

  afterEach(() => {
    {cleanup}
  });
});`
  },
  
  api_endpoint: {
    rest: `app.{method}('{path}', async (req, res) => {
  try {
    {validation}
    {logic}
    res.json({ success: true, data: result });
  } catch (error) {
    res.status(500).json({ error: error.message });
  }
});`,
    
    graphql: `const {name} = {
  type: {returnType},
  args: {
    {arguments}
  },
  resolve: async (parent, args, context) => {
    {resolverLogic}
  }
};`
  }
};

class ResponseGenerator {
  constructor() {
    this.responseCache = new Map();
    this.userPreferences = {
      verbosity: 'standard',
      codeStyle: 'modern',
      explanationDepth: 'balanced'
    };
    this.metrics = {
      totalResponses: 0,
      templateUsage: {},
      avgResponseLength: 0,
      relevanceScores: []
    };
  }

  async initialize() {
    try {
      // Load user preferences from memory
      await this.loadUserPreferences();
      
      logger.info('Response Generator initialized');
    } catch (error) {
      logger.error('Failed to initialize Response Generator', { 
        error: error.message 
      });
      throw error;
    }
  }

  async generateResponse(commandResult, context = {}) {
    try {
      // Determine response type
      const responseType = this.determineResponseType(commandResult);
      
      // Get relevant context
      const relevantContext = await this.gatherContext(commandResult, context);
      
      // Check for applicable patterns
      const patterns = await this.findApplicablePatterns(commandResult, relevantContext);
      
      // Generate response content
      const content = await this.craftResponse(
        responseType,
        commandResult,
        relevantContext,
        patterns
      );
      
      // Adapt to user preferences
      const adapted = this.adaptToPreferences(content);
      
      // Add metadata
      const response = {
        content: adapted,
        type: responseType,
        confidence: this.calculateConfidence(commandResult, relevantContext),
        metadata: {
          timestamp: Date.now(),
          context: relevantContext.summary,
          patterns: patterns.map(p => p.pattern_name),
          length: adapted.length
        }
      };
      
      // Track metrics
      this.trackMetrics(response);
      
      // Store for learning
      await this.storeResponse(commandResult, response);
      
      return response;
    } catch (error) {
      logger.error('Failed to generate response', { 
        error: error.message 
      });
      
      return this.generateErrorResponse(error);
    }
  }

  determineResponseType(commandResult) {
    if (!commandResult.success) return 'error';
    
    const actionTypeMap = {
      'create': 'code_generation',
      'modify': 'code_generation',
      'explain': 'explanation',
      'analyze': 'analysis',
      'search': 'search_results',
      'test': 'test_results',
      'help': 'help',
      'suggest': 'suggestions'
    };
    
    return actionTypeMap[commandResult.action] || 'success';
  }

  async gatherContext(commandResult, providedContext) {
    const context = {
      ...providedContext,
      projectContext: null,
      relevantMemories: [],
      recentPatterns: [],
      currentFile: null,
      summary: ''
    };
    
    // Get project context
    context.projectContext = await projectContextManager.getContextForQuery(
      commandResult.message || '',
      providedContext.projectId
    );
    
    // Search for relevant memories
    if (commandResult.target) {
      const query = typeof commandResult.target === 'string' ? 
        commandResult.target : 
        commandResult.target.name;
      
      context.relevantMemories = await memoryStoreV2.searchMemories(query, {
        limit: 5,
        projectId: providedContext.projectId
      });
    }
    
    // Get recent patterns
    context.recentPatterns = context.projectContext?.patterns?.slice(0, 3) || [];
    
    // Generate context summary
    context.summary = this.summarizeContext(context);
    
    return context;
  }

  async findApplicablePatterns(commandResult, context) {
    const patterns = [];
    
    // Check for code generation patterns
    if (commandResult.action === 'create' || commandResult.action === 'modify') {
      const target = commandResult.target;
      
      if (target && target.type === 'component') {
        // Look for component creation patterns
        const componentPatterns = context.recentPatterns.filter(p => 
          p.pattern_name?.includes('component') ||
          p.action_sequence?.includes('create_component')
        );
        patterns.push(...componentPatterns);
      }
      
      if (target && target.type === 'test') {
        // Look for test creation patterns
        const testPatterns = context.recentPatterns.filter(p => 
          p.pattern_name?.includes('test') ||
          p.action_sequence?.includes('create_test')
        );
        patterns.push(...testPatterns);
      }
    }
    
    return patterns;
  }

  async craftResponse(responseType, commandResult, context, patterns) {
    const verbosity = this.userPreferences.verbosity;
    const template = RESPONSE_TEMPLATES[responseType]?.[verbosity] || 
                    RESPONSE_TEMPLATES.success[verbosity];
    
    let content = '';
    
    switch (responseType) {
      case 'code_generation':
        content = await this.generateCodeResponse(commandResult, context, patterns, template);
        break;
        
      case 'explanation':
        content = await this.generateExplanationResponse(commandResult, context, template);
        break;
        
      case 'analysis':
        content = await this.generateAnalysisResponse(commandResult, context, template);
        break;
        
      case 'search_results':
        content = await this.generateSearchResponse(commandResult, context);
        break;
        
      case 'error':
        content = this.generateErrorContent(commandResult, template);
        break;
        
      default:
        content = this.generateDefaultResponse(commandResult, template);
    }
    
    return content;
  }

  async generateCodeResponse(commandResult, context, patterns, template) {
    const target = commandResult.target;
    const parameters = commandResult.parameters || {};
    
    // Determine language
    const language = this.detectLanguage(context, parameters);
    
    // Get code pattern
    let codePattern = null;
    
    if (target.type === 'component' && parameters.template === 'react') {
      codePattern = CODE_PATTERNS.react_component[
        parameters.style === 'class' ? 'class' : 'functional'
      ];
    } else if (target.type === 'test') {
      codePattern = CODE_PATTERNS.test[parameters.type || 'unit'];
    } else if (target.type === 'api') {
      codePattern = CODE_PATTERNS.api_endpoint[parameters.style || 'rest'];
    }
    
    // Apply patterns from project
    if (patterns.length > 0 && patterns[0].action_sequence) {
      // Use project-specific patterns
      const projectPattern = patterns[0];
      if (projectPattern.metadata?.codeTemplate) {
        codePattern = projectPattern.metadata.codeTemplate;
      }
    }
    
    // Generate code
    const code = this.fillCodeTemplate(codePattern || '// Generated code', {
      name: target.name || 'Component',
      props: parameters.props || '',
      state: parameters.state || '',
      className: parameters.className || 'container',
      content: parameters.content || '// Content here',
      ...parameters
    });
    
    // Generate explanation
    const explanation = this.generateCodeExplanation(code, target, parameters);
    
    // Fill response template
    return this.fillTemplate(template, {
      type: target.type,
      language,
      code,
      explanation,
      title: `${target.type} Implementation`,
      description: `Generated ${target.type} based on project patterns`,
      usage: this.generateUsageExample(target, parameters),
      notes: this.generateImplementationNotes(target, context)
    });
  }

  async generateExplanationResponse(commandResult, context, template) {
    const target = commandResult.target;
    const depth = commandResult.depth || 'standard';
    
    // Search for relevant documentation
    const docs = context.relevantMemories.filter(m => 
      m.metadata?.type === 'documentation' ||
      m.metadata?.type === 'explanation'
    );
    
    const explanation = {
      topic: target,
      summary: `Brief explanation of ${target}`,
      explanation: this.generateExplanation(target, docs, depth),
      overview: `Overview of ${target} in the context of this project`,
      example: this.generateExample(target, context),
      examples: this.generateMultipleExamples(target, context),
      related: this.findRelatedConcepts(target, context),
      practices: this.generateBestPractices(target, context)
    };
    
    return this.fillTemplate(template, explanation);
  }

  async generateAnalysisResponse(commandResult, context, template) {
    const target = commandResult.target;
    
    const analysis = {
      summary: `Analysis of ${target}`,
      findings: this.generateFindings(target, context),
      metrics: this.generateMetrics(target, context),
      recommendations: this.generateRecommendations(target, context),
      actions: this.generateActionItems(target, context)
    };
    
    return this.fillTemplate(template, analysis);
  }

  async generateSearchResponse(commandResult, context) {
    const results = commandResult.results || [];
    
    if (results.length === 0) {
      return 'No results found for your search.';
    }
    
    let response = `Found ${results.length} result${results.length > 1 ? 's' : ''}:\n\n`;
    
    for (const [index, result] of results.entries()) {
      response += `**${index + 1}.** ${result.content.substring(0, 150)}...\n`;
      
      if (result.metadata?.file) {
        response += `   📁 ${result.metadata.file}`;
      }
      
      if (result.similarity) {
        response += ` (${(result.similarity * 100).toFixed(1)}% match)`;
      }
      
      response += '\n\n';
    }
    
    return response;
  }

  generateErrorContent(commandResult, template) {
    return this.fillTemplate(template, {
      error: commandResult.error || 'An error occurred',
      suggestion: commandResult.suggestion?.message || 'Please try again',
      causes: this.identifyErrorCauses(commandResult.error),
      solutions: this.suggestSolutions(commandResult.error),
      prevention: this.suggestPrevention(commandResult.error)
    });
  }

  generateDefaultResponse(commandResult, template) {
    return this.fillTemplate(template, {
      message: commandResult.message || 'Operation completed',
      details: JSON.stringify(commandResult.parameters || {}, null, 2),
      nextSteps: this.suggestNextSteps(commandResult)
    });
  }

  fillTemplate(template, values) {
    let filled = template;
    
    for (const [key, value] of Object.entries(values)) {
      const placeholder = new RegExp(`\\{${key}\\}`, 'g');
      filled = filled.replace(placeholder, value || '');
    }
    
    return filled;
  }

  fillCodeTemplate(template, values) {
    let filled = template;
    
    for (const [key, value] of Object.entries(values)) {
      const placeholder = new RegExp(`\\{${key}\\}`, 'g');
      filled = filled.replace(placeholder, value || '');
    }
    
    return filled;
  }

  detectLanguage(context, parameters) {
    if (parameters.language) return parameters.language;
    
    // Detect from context
    const fileExtensions = {
      '.js': 'javascript',
      '.jsx': 'javascript',
      '.ts': 'typescript',
      '.tsx': 'typescript',
      '.py': 'python',
      '.java': 'java',
      '.go': 'go',
      '.rs': 'rust'
    };
    
    if (context.currentFile) {
      for (const [ext, lang] of Object.entries(fileExtensions)) {
        if (context.currentFile.endsWith(ext)) {
          return lang;
        }
      }
    }
    
    return 'javascript'; // Default
  }

  generateCodeExplanation(code, target, parameters) {
    const lines = code.split('\n');
    let explanation = `This ${target.type} `;
    
    if (parameters.template) {
      explanation += `uses the ${parameters.template} template `;
    }
    
    explanation += `and includes ${lines.length} lines of code. `;
    
    // Add specific explanations based on code patterns
    if (code.includes('async')) {
      explanation += 'It uses asynchronous operations. ';
    }
    
    if (code.includes('useState') || code.includes('this.state')) {
      explanation += 'It manages local state. ';
    }
    
    if (code.includes('export')) {
      explanation += 'It exports for use in other modules. ';
    }
    
    return explanation;
  }

  generateUsageExample(target, parameters) {
    if (target.type === 'component') {
      return `<${target.name} ${parameters.props ? 'prop="value"' : ''} />`;
    }
    
    if (target.type === 'function') {
      return `${target.name}(${parameters.arguments || ''});`;
    }
    
    if (target.type === 'class') {
      return `const instance = new ${target.name}();`;
    }
    
    return `// Usage example for ${target.name}`;
  }

  generateImplementationNotes(target, context) {
    const notes = [];
    
    if (context.projectContext?.settings?.framework) {
      notes.push(`Follows ${context.projectContext.settings.framework} conventions`);
    }
    
    if (context.recentPatterns.length > 0) {
      notes.push(`Based on ${context.recentPatterns.length} project patterns`);
    }
    
    notes.push('Remember to add appropriate error handling');
    notes.push('Consider adding unit tests');
    
    return notes.join('\n- ');
  }

  generateExplanation(topic, docs, depth) {
    let explanation = `${topic} is `;
    
    if (docs.length > 0) {
      // Use existing documentation
      explanation += docs[0].content.substring(0, 200);
    } else {
      // Generate generic explanation
      explanation += `a concept or component in your project. `;
      
      if (depth === 'detailed') {
        explanation += `It involves multiple aspects that work together to achieve specific functionality. `;
      }
    }
    
    return explanation;
  }

  generateExample(topic, context) {
    return `Example usage of ${topic} in your project context.`;
  }

  generateMultipleExamples(topic, context) {
    return [
      `1. Basic ${topic} example`,
      `2. Advanced ${topic} with options`,
      `3. ${topic} in production context`
    ].join('\n');
  }

  findRelatedConcepts(topic, context) {
    const related = [];
    
    // Find from context memories
    if (context.relevantMemories) {
      const concepts = context.relevantMemories
        .map(m => m.metadata?.relatedConcepts || [])
        .flat()
        .filter(Boolean);
      
      related.push(...new Set(concepts));
    }
    
    return related.join(', ') || `Concepts related to ${topic}`;
  }

  generateBestPractices(topic, context) {
    return [
      `Keep ${topic} simple and focused`,
      'Follow project conventions',
      'Add appropriate documentation',
      'Include error handling',
      'Write tests for critical paths'
    ].join('\n- ');
  }

  generateFindings(target, context) {
    return `Analysis findings for ${target}`;
  }

  generateMetrics(target, context) {
    return {
      complexity: 'Medium',
      maintainability: 'Good',
      testCoverage: '75%',
      performance: 'Optimal'
    };
  }

  generateRecommendations(target, context) {
    return [
      'Consider refactoring for better readability',
      'Add more comprehensive tests',
      'Update documentation'
    ].join('\n- ');
  }

  generateActionItems(target, context) {
    return [
      `Review ${target} implementation`,
      'Add missing tests',
      'Update related documentation'
    ].join('\n- ');
  }

  identifyErrorCauses(error) {
    return [
      'Invalid input parameters',
      'Missing required context',
      'System resource constraints'
    ].join('\n- ');
  }

  suggestSolutions(error) {
    return [
      'Verify input format',
      'Check required parameters',
      'Retry the operation'
    ].join('\n- ');
  }

  suggestPrevention(error) {
    return 'Validate inputs before processing';
  }

  suggestNextSteps(commandResult) {
    const steps = [];
    
    if (commandResult.action === 'create') {
      steps.push('Add tests for the new component');
      steps.push('Update documentation');
    }
    
    if (commandResult.action === 'modify') {
      steps.push('Run tests to verify changes');
      steps.push('Review the modifications');
    }
    
    return steps.join('\n- ') || 'Continue with your development';
  }

  adaptToPreferences(content) {
    // Adapt based on user preferences
    if (this.userPreferences.verbosity === 'brief') {
      // Shorten content
      const lines = content.split('\n');
      if (lines.length > 10) {
        return lines.slice(0, 10).join('\n') + '\n...';
      }
    }
    
    if (this.userPreferences.codeStyle === 'compact') {
      // Remove extra whitespace in code blocks
      content = content.replace(/\n\n+```/g, '\n```');
    }
    
    return content;
  }

  calculateConfidence(commandResult, context) {
    let confidence = 0.5;
    
    // Increase confidence based on context quality
    if (context.relevantMemories && context.relevantMemories.length > 0) {
      confidence += 0.2;
    }
    
    if (context.recentPatterns && context.recentPatterns.length > 0) {
      confidence += 0.2;
    }
    
    if (commandResult.success) {
      confidence += 0.1;
    }
    
    return Math.min(confidence, 1.0);
  }

  summarizeContext(context) {
    const parts = [];
    
    if (context.projectContext) {
      parts.push(`Project: ${context.projectContext.projectId}`);
    }
    
    if (context.relevantMemories) {
      parts.push(`${context.relevantMemories.length} relevant memories`);
    }
    
    if (context.recentPatterns) {
      parts.push(`${context.recentPatterns.length} patterns`);
    }
    
    return parts.join(', ');
  }

  async loadUserPreferences() {
    // Load from memory store
    const preferences = await memoryStoreV2.searchMemories('user preferences', {
      limit: 1,
      filter: { type: 'preferences' }
    });
    
    if (preferences.length > 0 && preferences[0].metadata) {
      Object.assign(this.userPreferences, preferences[0].metadata);
    }
  }

  async storeResponse(commandResult, response) {
    await memoryStoreV2.storeMemory(response.content, {
      type: 'generated_response',
      command: commandResult.action,
      target: commandResult.target,
      confidence: response.confidence,
      timestamp: response.metadata.timestamp
    });
  }

  generateErrorResponse(error) {
    return {
      content: `An error occurred: ${error.message}`,
      type: 'error',
      confidence: 1.0,
      metadata: {
        timestamp: Date.now(),
        error: error.message
      }
    };
  }

  trackMetrics(response) {
    this.metrics.totalResponses++;
    
    // Track template usage
    if (!this.metrics.templateUsage[response.type]) {
      this.metrics.templateUsage[response.type] = 0;
    }
    this.metrics.templateUsage[response.type]++;
    
    // Update average response length
    const prevAvg = this.metrics.avgResponseLength;
    this.metrics.avgResponseLength = 
      (prevAvg * (this.metrics.totalResponses - 1) + response.content.length) / 
      this.metrics.totalResponses;
    
    // Track relevance scores
    this.metrics.relevanceScores.push(response.confidence);
    if (this.metrics.relevanceScores.length > 100) {
      this.metrics.relevanceScores.shift();
    }
  }

  updatePreferences(preferences) {
    Object.assign(this.userPreferences, preferences);
    
    // Store preferences
    memoryStoreV2.storeMemory('User preferences updated', {
      type: 'preferences',
      ...this.userPreferences
    });
    
    logger.info('User preferences updated', preferences);
  }

  getMetrics() {
    const avgRelevance = this.metrics.relevanceScores.length > 0 ?
      this.metrics.relevanceScores.reduce((a, b) => a + b, 0) / this.metrics.relevanceScores.length :
      0;
    
    return {
      ...this.metrics,
      avgRelevance,
      preferences: this.userPreferences
    };
  }
}

export default new ResponseGenerator();