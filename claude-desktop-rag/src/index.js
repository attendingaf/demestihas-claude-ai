import winston from 'winston';
import extensionHooks from './claude-desktop/extension-hooks.js';
import memoryStore from './memory/memory-store.js';
import contextRetriever from './memory/context-retriever.js';
import contextInjector from './claude-desktop/context-injector.js';
import responseHandler from './claude-desktop/response-handler.js';
import { config, validateConfig } from '../config/rag-config.js';

const logger = winston.createLogger({
  level: config.logging.level,
  format: winston.format.combine(
    winston.format.timestamp(),
    winston.format.json()
  ),
  transports: [
    new winston.transports.Console({
      format: winston.format.simple()
    }),
    new winston.transports.File({ 
      filename: config.logging.file 
    })
  ]
});

class ClaudeDesktopRAG {
  constructor() {
    this.initialized = false;
  }

  /**
   * Initialize the RAG system
   */
  async initialize() {
    if (this.initialized) return;

    try {
      // Validate configuration
      validateConfig();
      
      // Initialize extension hooks
      await extensionHooks.initialize();
      
      this.initialized = true;
      logger.info('Claude Desktop RAG System initialized successfully');
      
      // Log system info
      this.logSystemInfo();
    } catch (error) {
      logger.error('Failed to initialize RAG system:', error);
      throw error;
    }
  }

  /**
   * Process a user prompt with RAG augmentation
   */
  async processPrompt(prompt, options = {}) {
    try {
      // Inject context into prompt
      const augmented = await contextInjector.injectContext(prompt, options);
      
      // Execute pre-prompt hooks
      const processed = await extensionHooks.handleEvent('pre-prompt', {
        prompt: augmented.augmentedPrompt,
        metadata: augmented.metadata
      });

      return processed;
    } catch (error) {
      logger.error('Failed to process prompt:', error);
      throw error;
    }
  }

  /**
   * Handle Claude's response
   */
  async handleResponse(response, context = {}) {
    try {
      // Process response
      const handled = await responseHandler.handleResponse(response, context);
      
      // Execute post-response hooks
      const processed = await extensionHooks.handleEvent('post-response', {
        response: handled.response,
        prompt: context.prompt,
        metadata: handled.extracted
      });

      return processed;
    } catch (error) {
      logger.error('Failed to handle response:', error);
      throw error;
    }
  }

  /**
   * Store a memory directly
   */
  async storeMemory(content, options = {}) {
    try {
      return await memoryStore.store(content, options);
    } catch (error) {
      logger.error('Failed to store memory:', error);
      throw error;
    }
  }

  /**
   * Retrieve relevant context
   */
  async retrieveContext(query, options = {}) {
    try {
      return await contextRetriever.retrieveWithPatterns(query, options);
    } catch (error) {
      logger.error('Failed to retrieve context:', error);
      throw error;
    }
  }

  /**
   * Get system statistics
   */
  async getStats() {
    try {
      const stats = await memoryStore.getStats();
      const hookStats = extensionHooks.getStats();
      const responseStats = responseHandler.getMetrics();

      return {
        memory: stats,
        hooks: hookStats,
        responses: responseStats,
        initialized: this.initialized
      };
    } catch (error) {
      logger.error('Failed to get stats:', error);
      return null;
    }
  }

  /**
   * Log system information
   */
  logSystemInfo() {
    logger.info('System Configuration:', {
      project: config.project.id,
      embeddingModel: config.openai.embeddingModel,
      maxContextItems: config.rag.maxContextItems,
      similarityThreshold: config.rag.similarityThreshold,
      patternDetection: {
        threshold: config.rag.patternThreshold,
        minOccurrences: config.rag.patternMinOccurrences
      }
    });
  }

  /**
   * Shutdown the system gracefully
   */
  async shutdown() {
    logger.info('Shutting down RAG system...');
    
    try {
      // Stop sync processes
      memoryStore.stopSync();
      
      // Close database connections
      await require('./core/sqlite-client.js').default.close();
      
      logger.info('RAG system shut down successfully');
    } catch (error) {
      logger.error('Error during shutdown:', error);
    }
  }
}

// Create singleton instance
const ragSystem = new ClaudeDesktopRAG();

// Export for use in Claude Desktop or other applications
export default ragSystem;

// If running standalone
if (import.meta.url === `file://${process.argv[1]}`) {
  async function main() {
    try {
      // Initialize system
      await ragSystem.initialize();
      
      logger.info('Claude Desktop RAG System is running');
      logger.info('Press Ctrl+C to shutdown');
      
      // Example usage (remove in production)
      if (process.env.NODE_ENV === 'development') {
        // Store a test memory
        await ragSystem.storeMemory('Claude Desktop RAG system initialized', {
          interactionType: 'system',
          metadata: { startup: true }
        });

        // Retrieve context for a query
        const context = await ragSystem.retrieveContext('How does the RAG system work?');
        logger.info('Retrieved context:', {
          items: context.items.length,
          patterns: context.patterns?.length || 0
        });

        // Get stats
        const stats = await ragSystem.getStats();
        logger.info('System stats:', stats);
      }
      
      // Keep process running
      process.stdin.resume();
      
      // Handle shutdown
      process.on('SIGINT', async () => {
        await ragSystem.shutdown();
        process.exit(0);
      });
      
      process.on('SIGTERM', async () => {
        await ragSystem.shutdown();
        process.exit(0);
      });
      
    } catch (error) {
      logger.error('Failed to start RAG system:', error);
      process.exit(1);
    }
  }

  main();
}