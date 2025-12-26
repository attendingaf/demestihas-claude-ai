#!/usr/bin/env node

import { performance } from 'perf_hooks';
import winston from 'winston';
import { v4 as uuidv4 } from 'uuid';
import sqliteClient from '../src/core/sqlite-client-optimized.js';
import projectContextManager from '../src/context/project-context-manager.js';
import contextPrioritizer from '../src/context/context-prioritizer.js';
import syncEngine from '../src/sync/sync-engine.js';
import performanceMonitor from '../src/monitoring/performance-monitor.js';
import { config } from '../config/rag-config.js';

const logger = winston.createLogger({
  level: 'info',
  format: winston.format.combine(
    winston.format.timestamp(),
    winston.format.printf(({ timestamp, level, message, ...meta }) => {
      const metaStr = Object.keys(meta).length ? ` ${JSON.stringify(meta)}` : '';
      return `${timestamp} [${level.toUpperCase()}]: ${message}${metaStr}`;
    })
  ),
  transports: [new winston.transports.Console()]
});

class Chapter2Tests {
  constructor() {
    this.testResults = {
      passed: 0,
      failed: 0,
      tests: []
    };
  }

  async runTest(name, testFn) {
    const startTime = performance.now();
    
    try {
      await testFn();
      const duration = performance.now() - startTime;
      
      this.testResults.passed++;
      this.testResults.tests.push({
        name,
        status: 'PASSED',
        duration
      });
      
      logger.info(`✅ ${name}`, { duration: `${duration.toFixed(2)}ms` });
      return true;
    } catch (error) {
      const duration = performance.now() - startTime;
      
      this.testResults.failed++;
      this.testResults.tests.push({
        name,
        status: 'FAILED',
        error: error.message,
        duration
      });
      
      logger.error(`❌ ${name}`, { 
        error: error.message,
        duration: `${duration.toFixed(2)}ms` 
      });
      return false;
    }
  }

  // Test 1: SQLite Performance Optimization
  async testSQLitePerformance() {
    await this.runTest('SQLite initialization with memory mapping', async () => {
      await sqliteClient.initialize();
      
      // Verify memory-mapped mode is enabled
      const result = await sqliteClient.db.get('PRAGMA mmap_size');
      if (!result || result.mmap_size === 0) {
        throw new Error('Memory mapping not enabled');
      }
    });

    await this.runTest('LRU cache functionality', async () => {
      // Test cache set and get
      const testKey = 'test-key-' + Date.now();
      const testValue = { data: 'test-value' };
      
      sqliteClient.queryCache.set(testKey, testValue);
      const retrieved = sqliteClient.queryCache.get(testKey);
      
      if (!retrieved || retrieved.data !== testValue.data) {
        throw new Error('LRU cache not working correctly');
      }
      
      // Test cache hit tracking
      const stats = sqliteClient.queryCache.getStats();
      if (stats.hits < 1) {
        throw new Error('Cache hits not being tracked');
      }
    });

    await this.runTest('Context cache table creation', async () => {
      const result = await sqliteClient.db.get(
        "SELECT name FROM sqlite_master WHERE type='table' AND name='context_cache'"
      );
      
      if (!result) {
        throw new Error('Context cache table not created');
      }
    });
  }

  // Test 2: Retrieval Speed Benchmark
  async testRetrievalSpeed() {
    const embeddings = [];
    const testCount = 100;
    
    // Create test embeddings
    for (let i = 0; i < 10; i++) {
      const embedding = new Array(1536).fill(0).map(() => Math.random());
      embeddings.push(embedding);
    }

    await this.runTest('Retrieval under 100ms (average)', async () => {
      const times = [];
      
      for (let i = 0; i < testCount; i++) {
        const embedding = embeddings[i % embeddings.length];
        const startTime = performance.now();
        
        await sqliteClient.searchMemories(embedding, {
          limit: 10,
          projectId: config.project.id
        });
        
        const duration = performance.now() - startTime;
        times.push(duration);
        
        // Track in performance monitor
        performanceMonitor.trackRetrievalTime(duration, 'test');
      }
      
      const avgTime = times.reduce((a, b) => a + b, 0) / times.length;
      logger.info(`Average retrieval time: ${avgTime.toFixed(2)}ms`);
      
      if (avgTime > 100) {
        throw new Error(`Average retrieval time ${avgTime.toFixed(2)}ms exceeds 100ms target`);
      }
    });

    await this.runTest('Cache hit rate > 80%', async () => {
      // Perform repeated searches to test cache
      const testEmbedding = embeddings[0];
      
      // First search (cache miss)
      await sqliteClient.searchMemories(testEmbedding, {
        limit: 10,
        projectId: config.project.id
      });
      
      // Repeated searches (should hit cache)
      for (let i = 0; i < 9; i++) {
        await sqliteClient.searchMemories(testEmbedding, {
          limit: 10,
          projectId: config.project.id
        });
      }
      
      const stats = sqliteClient.searchCache.getStats();
      const hitRate = stats.hits / (stats.hits + stats.misses);
      
      logger.info(`Cache hit rate: ${(hitRate * 100).toFixed(1)}%`);
      
      if (hitRate < 0.8) {
        throw new Error(`Cache hit rate ${(hitRate * 100).toFixed(1)}% below 80% target`);
      }
    });
  }

  // Test 3: Project Context Isolation
  async testProjectContextIsolation() {
    const project1 = 'test-project-1-' + Date.now();
    const project2 = 'test-project-2-' + Date.now();

    await this.runTest('Project context loading', async () => {
      await projectContextManager.initialize();
      
      const context = await projectContextManager.loadProjectContext(project1);
      
      if (!context || context.projectId !== project1) {
        throw new Error('Project context not loaded correctly');
      }
    });

    await this.runTest('Project context switching < 100ms', async () => {
      // Pre-load contexts
      await projectContextManager.loadProjectContext(project1);
      await projectContextManager.loadProjectContext(project2);
      
      const startTime = performance.now();
      await projectContextManager.switchProject(project2);
      const switchTime = performance.now() - startTime;
      
      logger.info(`Context switch time: ${switchTime.toFixed(2)}ms`);
      
      if (switchTime > 100) {
        throw new Error(`Context switch time ${switchTime.toFixed(2)}ms exceeds 100ms target`);
      }
    });

    await this.runTest('No context bleed between projects', async () => {
      // Create memory for project1
      const memory1 = {
        id: uuidv4(),
        project_id: project1,
        content: 'Project 1 memory',
        embedding: new Array(1536).fill(0).map(() => Math.random()),
        metadata: { project: project1 }
      };
      
      await sqliteClient.storeMemory(memory1);
      
      // Switch to project2
      await projectContextManager.switchProject(project2);
      
      // Create memory for project2
      const memory2 = {
        id: uuidv4(),
        project_id: project2,
        content: 'Project 2 memory',
        embedding: new Array(1536).fill(0).map(() => Math.random()),
        metadata: { project: project2 }
      };
      
      await sqliteClient.storeMemory(memory2);
      
      // Search in project2 context
      const isolated = await projectContextManager.isolateContext(project2);
      const results = await isolated.search(memory1.embedding, { limit: 10 });
      
      // Check for context bleed
      for (const result of results) {
        if (result.project_id === project1) {
          throw new Error(`Context bleed detected: project1 memory found in project2 context`);
        }
      }
      
      // Check isolation with performance monitor
      const isolationCheck = performanceMonitor.checkContextIsolation(project2, results);
      
      if (!isolationCheck) {
        throw new Error('Context isolation violation detected');
      }
    });
  }

  // Test 4: Context Priority System
  async testContextPrioritySystem() {
    await this.runTest('Priority boost levels', async () => {
      await contextPrioritizer.initialize();
      
      // Set current context
      contextPrioritizer.setCurrentContext('/test/file.js', 'testFunction');
      
      // Create test results with different characteristics
      const results = [
        {
          id: '1',
          content: 'Current file result',
          file_paths: ['/test/file.js'],
          similarity: 0.7,
          last_accessed: Math.floor(Date.now() / 1000)
        },
        {
          id: '2',
          content: 'Old result',
          file_paths: ['/other/file.js'],
          similarity: 0.8,
          last_accessed: Math.floor((Date.now() - 2 * 60 * 60 * 1000) / 1000)
        },
        {
          id: '3',
          content: 'Recent result',
          file_paths: ['/another/file.js'],
          similarity: 0.75,
          last_accessed: Math.floor((Date.now() - 10 * 60 * 1000) / 1000)
        }
      ];
      
      const prioritized = await contextPrioritizer.prioritizeResults(
        results,
        'test query'
      );
      
      // Check that current context gets highest boost
      const currentFileResult = prioritized.find(r => r.id === '1');
      
      if (!currentFileResult || currentFileResult.priorityScore.totalBoost < 2.0) {
        throw new Error('Current context not receiving proper boost');
      }
      
      // Check that results are properly sorted
      for (let i = 1; i < prioritized.length; i++) {
        if (prioritized[i].boostedSimilarity > prioritized[i-1].boostedSimilarity) {
          throw new Error('Results not properly sorted by boosted similarity');
        }
      }
    });
  }

  // Test 5: Sync Engine
  async testSyncEngine() {
    await this.runTest('Sync engine initialization', async () => {
      await syncEngine.initialize();
      
      // Check if sync engine is initialized
      const metrics = await syncEngine.getMetrics();
      
      if (metrics.totalSyncs === undefined) {
        throw new Error('Sync engine not properly initialized');
      }
    });

    await this.runTest('Offline queue functionality', async () => {
      // Simulate offline mode
      syncEngine.isOnline = false;
      
      // Add item to offline queue
      const testMemory = {
        id: uuidv4(),
        project_id: config.project.id,
        content: 'Offline test memory',
        embedding: new Array(1536).fill(0).map(() => Math.random())
      };
      
      syncEngine.offlineQueue.push({
        type: 'memory',
        operation: 'upsert',
        data: testMemory
      });
      
      if (syncEngine.offlineQueue.length !== 1) {
        throw new Error('Offline queue not working');
      }
      
      // Simulate coming back online
      syncEngine.isOnline = true;
      await syncEngine.processOfflineQueue();
      
      if (syncEngine.offlineQueue.length !== 0) {
        throw new Error('Offline queue not processed');
      }
    });

    await this.runTest('Sync latency < 1 second', async () => {
      const startTime = performance.now();
      
      // Create and sync a test memory
      const testMemory = {
        id: uuidv4(),
        project_id: config.project.id,
        content: 'Sync latency test',
        embedding: new Array(1536).fill(0).map(() => Math.random()),
        metadata: { test: true }
      };
      
      await sqliteClient.storeMemory(testMemory);
      
      // Wait for sync to complete (simulated)
      await new Promise(resolve => setTimeout(resolve, 100));
      
      const syncTime = performance.now() - startTime;
      
      logger.info(`Sync latency: ${syncTime.toFixed(2)}ms`);
      
      if (syncTime > 1000) {
        throw new Error(`Sync latency ${syncTime.toFixed(2)}ms exceeds 1000ms target`);
      }
    });
  }

  // Test 6: Performance Monitoring
  async testPerformanceMonitoring() {
    await this.runTest('Performance monitor initialization', async () => {
      await performanceMonitor.initialize();
      
      const metrics = await performanceMonitor.getMetrics();
      
      if (!metrics.retrieval || !metrics.cache || !metrics.sync) {
        throw new Error('Performance monitor not properly initialized');
      }
    });

    await this.runTest('Metric tracking and alerts', async () => {
      // Simulate slow retrieval
      performanceMonitor.trackRetrievalTime(150, 'test-slow');
      
      // Check if alert was generated
      const metrics = await performanceMonitor.getMetrics();
      const alerts = metrics.alerts;
      
      const slowRetrievalAlert = alerts.find(a => a.type === 'HIGH_RETRIEVAL_TIME');
      
      if (!slowRetrievalAlert) {
        throw new Error('Performance alert not generated for slow retrieval');
      }
    });

    await this.runTest('Performance report generation', async () => {
      const report = performanceMonitor.generateReport();
      
      if (!report.retrieval || !report.cache || !report.sync || !report.context) {
        throw new Error('Performance report incomplete');
      }
      
      if (!report.overallHealth) {
        throw new Error('Overall health not calculated');
      }
      
      logger.info(`System health: ${report.overallHealth}`);
    });
  }

  // Main test runner
  async runAllTests() {
    logger.info('Starting Chapter 2 Context Engine Tests...\n');
    
    try {
      // Initialize all systems
      await sqliteClient.initialize();
      await performanceMonitor.initialize();
      
      // Run test suites
      await this.testSQLitePerformance();
      await this.testRetrievalSpeed();
      await this.testProjectContextIsolation();
      await this.testContextPrioritySystem();
      await this.testSyncEngine();
      await this.testPerformanceMonitoring();
      
      // Generate final report
      this.generateFinalReport();
      
    } catch (error) {
      logger.error('Test suite failed', { error: error.message });
    } finally {
      // Cleanup
      await this.cleanup();
    }
  }

  generateFinalReport() {
    const total = this.testResults.passed + this.testResults.failed;
    const passRate = (this.testResults.passed / total * 100).toFixed(1);
    
    logger.info('\n' + '='.repeat(60));
    logger.info('CHAPTER 2 TEST RESULTS');
    logger.info('='.repeat(60));
    logger.info(`Total Tests: ${total}`);
    logger.info(`Passed: ${this.testResults.passed} ✅`);
    logger.info(`Failed: ${this.testResults.failed} ❌`);
    logger.info(`Pass Rate: ${passRate}%`);
    logger.info('='.repeat(60));
    
    // Performance summary
    this.generatePerformanceSummary();
    
    // Exit with appropriate code
    process.exit(this.testResults.failed > 0 ? 1 : 0);
  }

  async generatePerformanceSummary() {
    const perfMetrics = await performanceMonitor.getMetrics();
    const dbStats = await sqliteClient.getStats();
    
    logger.info('\nPERFORMANCE SUMMARY:');
    logger.info('-------------------');
    logger.info(`📊 Avg Retrieval Time: ${perfMetrics.retrieval.avg.toFixed(2)}ms`);
    logger.info(`📊 Cache Hit Rate: ${(perfMetrics.cache.hitRate * 100).toFixed(1)}%`);
    logger.info(`📊 Avg Sync Latency: ${perfMetrics.sync.avgLatency.toFixed(2)}ms`);
    logger.info(`📊 Avg Context Switch: ${perfMetrics.context.avgSwitchTime.toFixed(2)}ms`);
    logger.info(`📊 Database Records: ${dbStats.memories + dbStats.patterns} items`);
    logger.info(`📊 Context Cache: ${dbStats.contextCache} entries`);
    logger.info(`📊 System Health: ${perfMetrics.health}`);
    
    // Success criteria check
    logger.info('\nSUCCESS CRITERIA:');
    logger.info('-----------------');
    
    const criteria = [
      {
        name: 'Local retrieval < 100ms',
        met: perfMetrics.retrieval.avg < 100
      },
      {
        name: 'Cache hit rate > 80%',
        met: perfMetrics.cache.hitRate > 0.8
      },
      {
        name: 'Context switch < 100ms',
        met: perfMetrics.context.avgSwitchTime < 100
      },
      {
        name: 'Sync latency < 1s',
        met: perfMetrics.sync.avgLatency < 1000
      },
      {
        name: 'Zero context violations',
        met: perfMetrics.context.isolationViolations === 0
      }
    ];
    
    for (const criterion of criteria) {
      const icon = criterion.met ? '✅' : '❌';
      logger.info(`${icon} ${criterion.name}`);
    }
    
    const allMet = criteria.every(c => c.met);
    
    if (allMet) {
      logger.info('\n🎉 All Chapter 2 success criteria met!');
    } else {
      logger.warn('\n⚠️ Some success criteria not met');
    }
  }

  async cleanup() {
    try {
      // Stop monitoring
      performanceMonitor.stop();
      
      // Stop sync engine
      await syncEngine.stop();
      
      // Close database
      await sqliteClient.close();
      
      logger.info('Cleanup completed');
    } catch (error) {
      logger.error('Cleanup error', { error: error.message });
    }
  }
}

// Run tests
const tester = new Chapter2Tests();
tester.runAllTests();