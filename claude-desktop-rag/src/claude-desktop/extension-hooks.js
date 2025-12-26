import winston from 'winston';
import memoryStore from '../memory/memory-store.js';
import contextRetriever from '../memory/context-retriever.js';
import patternDetector from '../patterns/pattern-detector.js';
import patternMatcher from '../patterns/pattern-matcher.js';
import { config } from '../../config/rag-config.js';

const logger = winston.createLogger({
  level: config.logging.level,
  format: winston.format.json(),
  transports: [
    new winston.transports.Console(),
    new winston.transports.File({ filename: config.logging.file })
  ]
});

class ExtensionHooks {
  constructor() {
    this.initialized = false;
    this.hooks = new Map();
    this.interceptors = new Map();
  }

  /**
   * Initialize Claude Desktop extension hooks
   */
  async initialize() {
    if (this.initialized) return;

    try {
      // Initialize components
      await memoryStore.initialize();
      await patternDetector.initialize();

      // Register default hooks
      this.registerDefaultHooks();

      this.initialized = true;
      logger.info('Claude Desktop extension hooks initialized');
    } catch (error) {
      logger.error('Failed to initialize extension hooks', { error: error.message });
      throw error;
    }
  }

  /**
   * Register default hooks
   */
  registerDefaultHooks() {
    // Pre-prompt hook - augments user input with context
    this.registerHook('pre-prompt', async (data) => {
      return this.prePromptHook(data);
    });

    // Post-response hook - processes Claude's response
    this.registerHook('post-response', async (data) => {
      return this.postResponseHook(data);
    });

    // Tool-call hook - intercepts tool usage
    this.registerHook('tool-call', async (data) => {
      return this.toolCallHook(data);
    });

    // Error hook - handles errors
    this.registerHook('error', async (data) => {
      return this.errorHook(data);
    });
  }

  /**
   * Register a hook
   */
  registerHook(name, handler) {
    if (!this.hooks.has(name)) {
      this.hooks.set(name, []);
    }
    this.hooks.get(name).push(handler);
    logger.debug('Hook registered', { name });
  }

  /**
   * Register an interceptor
   */
  registerInterceptor(name, handler) {
    this.interceptors.set(name, handler);
    logger.debug('Interceptor registered', { name });
  }

  /**
   * Execute hooks for an event
   */
  async executeHooks(name, data) {
    const handlers = this.hooks.get(name) || [];
    let result = data;

    for (const handler of handlers) {
      try {
        result = await handler(result) || result;
      } catch (error) {
        logger.error('Hook execution failed', {
          hook: name,
          error: error.message
        });
      }
    }

    return result;
  }

  /**
   * Pre-prompt hook - augments user input
   */
  async prePromptHook(data) {
    const { prompt, metadata = {} } = data;

    try {
      // Retrieve relevant context
      const context = await contextRetriever.retrieveWithPatterns(prompt, {
        maxItems: 10,
        contextType: metadata.contextType || 'all'
      });

      // Check for matching patterns
      let suggestedActions = [];
      if (context.patterns && context.patterns.length > 0) {
        const topPattern = context.patterns[0];
        if (topPattern.auto_apply && topPattern.similarity > 0.9) {
          const applied = await patternMatcher.applyPattern(topPattern, {
            query: prompt,
            ...metadata
          });
          
          if (applied.success) {
            suggestedActions = applied.actions;
          }
        }
      }

      // Store the interaction
      await memoryStore.store(prompt, {
        interactionType: 'user_prompt',
        metadata: {
          ...metadata,
          hasContext: context.items.length > 0,
          hasPatterns: (context.patterns?.length || 0) > 0
        }
      });

      // Record for pattern detection
      await patternDetector.recordInteraction({
        content: prompt,
        metadata
      });

      // Augment the prompt with context
      const augmented = {
        originalPrompt: prompt,
        context: context.items,
        suggestedActions,
        metadata: {
          ...metadata,
          contextItems: context.items.length,
          patterns: context.patterns?.length || 0
        }
      };

      logger.info('Prompt augmented', {
        original: prompt.substring(0, 50),
        contextItems: context.items.length,
        patterns: context.patterns?.length || 0
      });

      return augmented;
    } catch (error) {
      logger.error('Pre-prompt hook failed', { error: error.message });
      return data;
    }
  }

  /**
   * Post-response hook - processes Claude's response
   */
  async postResponseHook(data) {
    const { response, prompt, metadata = {} } = data;

    try {
      // Store the response
      await memoryStore.store(response, {
        interactionType: 'assistant_response',
        metadata: {
          ...metadata,
          promptReference: prompt
        }
      });

      // Extract any file paths or tools mentioned
      const extracted = this.extractMetadata(response);

      if (extracted.filePaths.length > 0 || extracted.tools.length > 0) {
        // Store enriched version
        await memoryStore.store(response, {
          interactionType: 'enriched_response',
          filePaths: extracted.filePaths,
          toolChain: extracted.tools,
          metadata: {
            ...metadata,
            extracted: true
          }
        });
      }

      // Record for pattern detection
      await patternDetector.recordInteraction({
        content: response,
        filePaths: extracted.filePaths,
        toolChain: extracted.tools,
        metadata
      });

      logger.debug('Response processed', {
        length: response.length,
        filePaths: extracted.filePaths.length,
        tools: extracted.tools.length
      });

      return {
        ...data,
        extracted
      };
    } catch (error) {
      logger.error('Post-response hook failed', { error: error.message });
      return data;
    }
  }

  /**
   * Tool-call hook - intercepts tool usage
   */
  async toolCallHook(data) {
    const { tool, parameters, result, metadata = {} } = data;

    try {
      // Store tool usage
      await memoryStore.store(
        `Tool: ${tool}\nParameters: ${JSON.stringify(parameters)}\nResult: ${JSON.stringify(result)}`,
        {
          interactionType: 'tool_usage',
          toolChain: [tool],
          metadata: {
            ...metadata,
            tool,
            parameters,
            resultSummary: this.summarizeResult(result)
          },
          successScore: result.error ? 0.5 : 1.0
        }
      );

      // Record for pattern detection
      await patternDetector.recordInteraction({
        content: `${tool} ${JSON.stringify(parameters)}`,
        toolChain: [tool],
        success: !result.error,
        metadata
      });

      logger.debug('Tool usage recorded', { tool });

      return data;
    } catch (error) {
      logger.error('Tool-call hook failed', { error: error.message });
      return data;
    }
  }

  /**
   * Error hook - handles errors
   */
  async errorHook(data) {
    const { error, context, metadata = {} } = data;

    try {
      // Store error for learning
      await memoryStore.store(
        `Error: ${error.message}\nContext: ${JSON.stringify(context)}`,
        {
          interactionType: 'error',
          metadata: {
            ...metadata,
            errorType: error.name,
            errorStack: error.stack
          },
          successScore: 0
        }
      );

      // Record for pattern detection (to avoid repeating errors)
      await patternDetector.recordInteraction({
        content: error.message,
        success: false,
        metadata: {
          ...metadata,
          errorType: error.name
        }
      });

      logger.error('Error recorded', {
        type: error.name,
        message: error.message
      });

      return data;
    } catch (err) {
      logger.error('Error hook failed', { error: err.message });
      return data;
    }
  }

  /**
   * Extract metadata from text
   */
  extractMetadata(text) {
    const filePaths = [];
    const tools = [];

    // Extract file paths (simple regex)
    const pathRegex = /(?:\/[\w.-]+)+(?:\/[\w.-]+)*|(?:[a-zA-Z]:[\\/][\w.-]+(?:[\\/][\w.-]+)*)/g;
    const pathMatches = text.match(pathRegex) || [];
    filePaths.push(...pathMatches);

    // Extract tool mentions (customize based on your tools)
    const toolKeywords = ['search', 'retrieve', 'analyze', 'generate', 'transform'];
    for (const keyword of toolKeywords) {
      if (text.toLowerCase().includes(keyword)) {
        tools.push(keyword);
      }
    }

    return {
      filePaths: [...new Set(filePaths)],
      tools: [...new Set(tools)]
    };
  }

  /**
   * Summarize result (for storage)
   */
  summarizeResult(result) {
    if (!result) return 'null';
    if (typeof result === 'string') return result.substring(0, 100);
    if (typeof result === 'object') {
      if (result.error) return `Error: ${result.error}`;
      if (result.data) return `Data: ${JSON.stringify(result.data).substring(0, 100)}`;
      return JSON.stringify(result).substring(0, 100);
    }
    return String(result).substring(0, 100);
  }

  /**
   * Handle Claude Desktop events
   */
  async handleEvent(eventType, data) {
    if (!this.initialized) {
      await this.initialize();
    }

    // Check for interceptor
    const interceptor = this.interceptors.get(eventType);
    if (interceptor) {
      const intercepted = await interceptor(data);
      if (intercepted === false) {
        logger.debug('Event intercepted and blocked', { eventType });
        return null;
      }
      data = intercepted || data;
    }

    // Execute hooks
    return this.executeHooks(eventType, data);
  }

  /**
   * Get hook statistics
   */
  getStats() {
    return {
      hooks: Array.from(this.hooks.keys()),
      interceptors: Array.from(this.interceptors.keys()),
      initialized: this.initialized
    };
  }
}

export default new ExtensionHooks();