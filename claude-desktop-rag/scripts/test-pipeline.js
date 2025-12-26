#!/usr/bin/env node

import { promises as fs } from 'fs';
import winston from 'winston';
import embeddingService from '../src/core/embedding-service.js';
import sqliteClient from '../src/core/sqlite-client.js';
import supabaseClient from '../src/core/supabase-client.js';
import memoryStore from '../src/memory/memory-store.js';
import contextRetriever from '../src/memory/context-retriever.js';
import patternDetector from '../src/patterns/pattern-detector.js';
import extensionHooks from '../src/claude-desktop/extension-hooks.js';
import contextInjector from '../src/claude-desktop/context-injector.js';
import responseHandler from '../src/claude-desktop/response-handler.js';

const logger = winston.createLogger({
  level: 'info',
  format: winston.format.combine(
    winston.format.colorize(),
    winston.format.simple()
  ),
  transports: [new winston.transports.Console()]
});

class TestPipeline {
  constructor() {
    this.tests = [];
    this.results = {
      passed: 0,
      failed: 0,
      errors: []
    };
  }

  /**
   * Run all tests
   */
  async run() {
    logger.info('Starting RAG System Test Pipeline...\n');

    try {
      // Initialize system
      await this.initialize();

      // Run test suites
      await this.testEmbeddingService();
      await this.testDatabaseConnections();
      await this.testMemoryStorage();
      await this.testContextRetrieval();
      await this.testPatternDetection();
      await this.testClaudeIntegration();

      // Print results
      this.printResults();
    } catch (error) {
      logger.error('Test pipeline failed:', error);
      process.exit(1);
    }
  }

  /**
   * Initialize system
   */
  async initialize() {
    logger.info('Initializing system components...');

    try {
      await sqliteClient.initialize();
      await supabaseClient.initialize();
      await memoryStore.initialize();
      await extensionHooks.initialize();

      this.passed('System initialization');
    } catch (error) {
      this.failed('System initialization', error);
      throw error;
    }
  }

  /**
   * Test embedding service
   */
  async testEmbeddingService() {
    logger.info('\n=== Testing Embedding Service ===');

    // Test single embedding
    try {
      const embedding = await embeddingService.generateEmbedding('Test query for RAG system');
      
      if (embedding && embedding.length === 1536) {
        this.passed('Single embedding generation');
      } else {
        this.failed('Single embedding generation', 'Invalid embedding dimensions');
      }
    } catch (error) {
      this.failed('Single embedding generation', error);
    }

    // Test batch embeddings
    try {
      const texts = [
        'First test text',
        'Second test text',
        'Third test text'
      ];
      
      const embeddings = await embeddingService.generateEmbeddings(texts);
      
      if (embeddings.length === 3 && embeddings.every(e => e.length === 1536)) {
        this.passed('Batch embedding generation');
      } else {
        this.failed('Batch embedding generation', 'Invalid batch embeddings');
      }
    } catch (error) {
      this.failed('Batch embedding generation', error);
    }

    // Test similarity calculation
    try {
      const emb1 = await embeddingService.generateEmbedding('Claude Desktop RAG system');
      const emb2 = await embeddingService.generateEmbedding('Claude Desktop retrieval augmented generation');
      
      const similarity = embeddingService.cosineSimilarity(emb1, emb2);
      
      if (similarity > 0.7 && similarity <= 1.0) {
        this.passed('Similarity calculation');
      } else {
        this.failed('Similarity calculation', `Unexpected similarity: ${similarity}`);
      }
    } catch (error) {
      this.failed('Similarity calculation', error);
    }
  }

  /**
   * Test database connections
   */
  async testDatabaseConnections() {
    logger.info('\n=== Testing Database Connections ===');

    // Test SQLite
    try {
      const stats = await sqliteClient.getStats();
      
      if (stats !== undefined) {
        this.passed('SQLite connection');
        logger.info(`  SQLite stats: ${JSON.stringify(stats)}`);
      } else {
        this.failed('SQLite connection', 'Could not get stats');
      }
    } catch (error) {
      this.failed('SQLite connection', error);
    }

    // Test Supabase
    try {
      const stats = await supabaseClient.getStats();
      
      if (stats !== undefined) {
        this.passed('Supabase connection');
        logger.info(`  Supabase stats: ${JSON.stringify(stats)}`);
      } else {
        this.failed('Supabase connection', 'Could not get stats');
      }
    } catch (error) {
      this.failed('Supabase connection', error);
    }
  }

  /**
   * Test memory storage
   */
  async testMemoryStorage() {
    logger.info('\n=== Testing Memory Storage ===');

    // Test storing single memory
    try {
      const memory = await memoryStore.store('Test memory content for RAG system', {
        interactionType: 'test',
        metadata: { test: true }
      });

      if (memory && memory.id) {
        this.passed('Store single memory');
        logger.info(`  Memory ID: ${memory.id}`);
      } else {
        this.failed('Store single memory', 'No memory ID returned');
      }
    } catch (error) {
      this.failed('Store single memory', error);
    }

    // Test batch storage
    try {
      const memories = await memoryStore.storeBatch([
        { content: 'Batch memory 1' },
        { content: 'Batch memory 2' },
        { content: 'Batch memory 3' }
      ]);

      if (memories.length === 3) {
        this.passed('Store batch memories');
      } else {
        this.failed('Store batch memories', `Expected 3, got ${memories.length}`);
      }
    } catch (error) {
      this.failed('Store batch memories', error);
    }

    // Test retrieval
    try {
      const results = await memoryStore.retrieve('RAG system test', {
        limit: 5
      });

      if (Array.isArray(results)) {
        this.passed('Retrieve memories');
        logger.info(`  Retrieved ${results.length} memories`);
      } else {
        this.failed('Retrieve memories', 'Invalid results format');
      }
    } catch (error) {
      this.failed('Retrieve memories', error);
    }
  }

  /**
   * Test context retrieval
   */
  async testContextRetrieval() {
    logger.info('\n=== Testing Context Retrieval ===');

    // Test basic context retrieval
    try {
      const context = await contextRetriever.retrieveContext('Claude Desktop integration', {
        maxItems: 10
      });

      if (context && context.items) {
        this.passed('Basic context retrieval');
        logger.info(`  Context items: ${context.items.length}`);
      } else {
        this.failed('Basic context retrieval', 'No context returned');
      }
    } catch (error) {
      this.failed('Basic context retrieval', error);
    }

    // Test context with patterns
    try {
      const context = await contextRetriever.retrieveWithPatterns('Test query with patterns');

      if (context && context.items) {
        this.passed('Context with patterns');
        logger.info(`  Patterns found: ${context.patterns?.length || 0}`);
      } else {
        this.failed('Context with patterns', 'No context returned');
      }
    } catch (error) {
      this.failed('Context with patterns', error);
    }
  }

  /**
   * Test pattern detection
   */
  async testPatternDetection() {
    logger.info('\n=== Testing Pattern Detection ===');

    // Test recording interactions
    try {
      // Record similar interactions
      for (let i = 0; i < 3; i++) {
        await patternDetector.recordInteraction({
          content: 'Create a new React component',
          toolChain: ['create-file', 'edit-file'],
          filePaths: ['src/components/NewComponent.jsx'],
          success: true
        });
      }

      this.passed('Record pattern interactions');
    } catch (error) {
      this.failed('Record pattern interactions', error);
    }

    // Test pattern detection
    try {
      await patternDetector.detectPatterns();
      this.passed('Pattern detection');
    } catch (error) {
      this.failed('Pattern detection', error);
    }
  }

  /**
   * Test Claude Desktop integration
   */
  async testClaudeIntegration() {
    logger.info('\n=== Testing Claude Desktop Integration ===');

    // Test context injection
    try {
      const result = await contextInjector.injectContext('Test prompt for context injection');

      if (result && result.augmentedPrompt) {
        this.passed('Context injection');
        logger.info(`  Augmented length: ${result.augmentedPrompt.length}`);
      } else {
        this.failed('Context injection', 'No augmented prompt');
      }
    } catch (error) {
      this.failed('Context injection', error);
    }

    // Test response handling
    try {
      const handled = await responseHandler.handleResponse(
        'This is a test response with ```javascript\nconst test = true;\n```',
        { prompt: 'Test prompt' }
      );

      if (handled && handled.type) {
        this.passed('Response handling');
        logger.info(`  Response type: ${handled.type}`);
      } else {
        this.failed('Response handling', 'No response type detected');
      }
    } catch (error) {
      this.failed('Response handling', error);
    }

    // Test extension hooks
    try {
      const result = await extensionHooks.handleEvent('pre-prompt', {
        prompt: 'Test hook execution',
        metadata: {}
      });

      if (result) {
        this.passed('Extension hooks');
      } else {
        this.failed('Extension hooks', 'No result from hooks');
      }
    } catch (error) {
      this.failed('Extension hooks', error);
    }
  }

  /**
   * Mark test as passed
   */
  passed(testName) {
    this.results.passed++;
    logger.info(`  ✓ ${testName}`);
  }

  /**
   * Mark test as failed
   */
  failed(testName, error) {
    this.results.failed++;
    const errorMsg = error instanceof Error ? error.message : String(error);
    this.results.errors.push({ test: testName, error: errorMsg });
    logger.error(`  ✗ ${testName}: ${errorMsg}`);
  }

  /**
   * Print test results
   */
  printResults() {
    logger.info('\n' + '='.repeat(50));
    logger.info('TEST RESULTS');
    logger.info('='.repeat(50));
    
    const total = this.results.passed + this.results.failed;
    const passRate = ((this.results.passed / total) * 100).toFixed(1);

    logger.info(`Total Tests: ${total}`);
    logger.info(`Passed: ${this.results.passed} (${passRate}%)`);
    logger.info(`Failed: ${this.results.failed}`);

    if (this.results.failed > 0) {
      logger.info('\nFailed Tests:');
      for (const error of this.results.errors) {
        logger.error(`  - ${error.test}: ${error.error}`);
      }
    }

    logger.info('\n' + '='.repeat(50));

    if (this.results.failed === 0) {
      logger.info('✅ All tests passed!');
      process.exit(0);
    } else {
      logger.error('❌ Some tests failed');
      process.exit(1);
    }
  }
}

// Run tests
const pipeline = new TestPipeline();
pipeline.run().catch(error => {
  logger.error('Fatal error:', error);
  process.exit(1);
});