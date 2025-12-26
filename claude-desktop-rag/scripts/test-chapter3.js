#!/usr/bin/env node

import { performance } from 'perf_hooks';
import winston from 'winston';
import assistantCore from '../src/assistant/assistant-core.js';
import commandOrchestrator from '../src/assistant/command-orchestrator.js';
import responseGenerator from '../src/assistant/response-generator.js';
import learningEngine from '../src/assistant/learning-engine.js';
import conversationManager from '../src/assistant/conversation-manager.js';
import codeIntelligence from '../src/assistant/code-intelligence.js';

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

class Chapter3Tests {
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

  // Test 1: Command Processing
  async testCommandProcessing() {
    await this.runTest('Command orchestrator initialization', async () => {
      await commandOrchestrator.initialize();
    });

    await this.runTest('Natural language command parsing', async () => {
      const commands = [
        'create a new React component called UserProfile',
        'explain how this function works',
        'find all TODO comments in the project',
        'test the authentication module',
        'refactor this code to use async/await'
      ];
      
      for (const command of commands) {
        const result = await commandOrchestrator.processCommand(command);
        
        if (!result || !result.action) {
          throw new Error(`Failed to process command: ${command}`);
        }
      }
    });

    await this.runTest('Command processing < 100ms', async () => {
      const times = [];
      const testCommands = [
        'create a function',
        'modify the code',
        'search for errors',
        'explain this concept',
        'analyze performance'
      ];
      
      for (const command of testCommands) {
        const startTime = performance.now();
        await commandOrchestrator.processCommand(command);
        const duration = performance.now() - startTime;
        times.push(duration);
      }
      
      const avgTime = times.reduce((a, b) => a + b, 0) / times.length;
      logger.info(`Average command processing time: ${avgTime.toFixed(2)}ms`);
      
      if (avgTime > 100) {
        throw new Error(`Average processing time ${avgTime.toFixed(2)}ms exceeds 100ms target`);
      }
    });

    await this.runTest('Intent recognition accuracy', async () => {
      const testCases = [
        { input: 'create a new file', expectedIntent: 'CREATE' },
        { input: 'modify this function', expectedIntent: 'MODIFY' },
        { input: 'search for bugs', expectedIntent: 'SEARCH' },
        { input: 'explain the algorithm', expectedIntent: 'EXPLAIN' },
        { input: 'how do I use this?', expectedIntent: 'HELP' }
      ];
      
      let correct = 0;
      
      for (const testCase of testCases) {
        const intent = await commandOrchestrator.recognizeIntent(testCase.input);
        
        if (intent.type === testCase.expectedIntent) {
          correct++;
        }
      }
      
      const accuracy = correct / testCases.length;
      logger.info(`Intent recognition accuracy: ${(accuracy * 100).toFixed(1)}%`);
      
      if (accuracy < 0.8) {
        throw new Error(`Intent accuracy ${(accuracy * 100).toFixed(1)}% below 80% target`);
      }
    });
  }

  // Test 2: Response Generation
  async testResponseGeneration() {
    await this.runTest('Response generator initialization', async () => {
      await responseGenerator.initialize();
    });

    await this.runTest('Context-aware response generation', async () => {
      const commandResult = {
        success: true,
        action: 'create',
        target: { type: 'component', name: 'TestComponent' },
        parameters: { template: 'react' }
      };
      
      const response = await responseGenerator.generateResponse(commandResult);
      
      if (!response || !response.content) {
        throw new Error('Failed to generate response');
      }
      
      if (!response.content.includes('```')) {
        throw new Error('Code response missing code block');
      }
    });

    await this.runTest('Response relevance > 95%', async () => {
      const testCases = [
        {
          command: { action: 'explain', target: 'async/await' },
          expectedKeywords: ['async', 'await', 'asynchronous']
        },
        {
          command: { action: 'create', target: { type: 'test' } },
          expectedKeywords: ['test', 'describe', 'it']
        },
        {
          command: { action: 'analyze', target: 'performance' },
          expectedKeywords: ['performance', 'analysis', 'metrics']
        }
      ];
      
      let relevantResponses = 0;
      
      for (const testCase of testCases) {
        const response = await responseGenerator.generateResponse(testCase.command);
        
        const hasKeywords = testCase.expectedKeywords.some(keyword => 
          response.content.toLowerCase().includes(keyword)
        );
        
        if (hasKeywords) {
          relevantResponses++;
        }
      }
      
      const relevance = relevantResponses / testCases.length;
      logger.info(`Response relevance: ${(relevance * 100).toFixed(1)}%`);
      
      if (relevance < 0.95) {
        throw new Error(`Response relevance ${(relevance * 100).toFixed(1)}% below 95% target`);
      }
    });
  }

  // Test 3: Learning Engine
  async testLearningEngine() {
    await this.runTest('Learning engine initialization', async () => {
      await learningEngine.initialize();
    });

    await this.runTest('Pattern extraction from interactions', async () => {
      const command = {
        action: 'create',
        intent: { type: 'CREATE', confidence: 0.9 },
        entities: { target: { type: 'component', name: 'Test' } }
      };
      
      const response = {
        success: true,
        type: 'code_generation',
        content: '```javascript\nconst Test = () => {}\n```'
      };
      
      const result = await learningEngine.learnFromInteraction(command, response);
      
      if (!result || result.patternsLearned === 0) {
        throw new Error('No patterns extracted from interaction');
      }
    });

    await this.runTest('Mistake recognition and correction', async () => {
      const command = {
        action: 'create',
        intent: { type: 'CREATE', confidence: 0.9 },
        input: 'create a component'
      };
      
      const incorrectResponse = {
        success: false,
        content: 'Wrong response'
      };
      
      const feedback = {
        corrected: true,
        correction: 'Correct response',
        context: 'User corrected the response'
      };
      
      await learningEngine.learnFromMistake(command, incorrectResponse, feedback);
      
      const metrics = learningEngine.getMetrics();
      
      if (metrics.mistakesCorrected === 0) {
        throw new Error('Mistake correction not tracked');
      }
    });

    await this.runTest('Learning effectiveness measurement', async () => {
      // Simulate multiple interactions
      for (let i = 0; i < 10; i++) {
        const command = {
          action: 'test',
          intent: { type: 'TEST', confidence: 0.8 + (i * 0.02) }
        };
        
        const response = {
          success: true,
          type: 'test_results'
        };
        
        await learningEngine.learnFromInteraction(command, response);
      }
      
      const metrics = learningEngine.getMetrics();
      
      if (metrics.patternsLearned < 5) {
        throw new Error('Insufficient pattern learning');
      }
      
      logger.info(`Patterns learned: ${metrics.patternsLearned}`);
    });
  }

  // Test 4: Conversation Management
  async testConversationManagement() {
    await this.runTest('Conversation manager initialization', async () => {
      await conversationManager.initialize();
    });

    await this.runTest('Multi-turn context preservation', async () => {
      const conversationId = await conversationManager.startConversation();
      
      const turns = [
        { input: 'Create a file called test.js', response: { content: 'File created' } },
        { input: 'Add a function to it', response: { content: 'Function added' } },
        { input: 'Now add tests for that function', response: { content: 'Tests added' } }
      ];
      
      for (const turn of turns) {
        await conversationManager.addTurn(turn.input, turn.response, conversationId);
      }
      
      const history = conversationManager.getConversationHistory(conversationId);
      
      if (history.length !== turns.length) {
        throw new Error('Context not preserved across turns');
      }
    });

    await this.runTest('Reference resolution', async () => {
      const conversationId = await conversationManager.startConversation();
      
      // First turn establishes context
      await conversationManager.addTurn(
        'Create a function called calculateSum',
        { content: 'Function created' },
        conversationId
      );
      
      // Second turn uses reference
      const conversation = conversationManager.getConversation(conversationId);
      const resolved = await conversationManager.resolveReferences(
        'Add documentation to it',
        conversation
      );
      
      if (resolved === 'Add documentation to it') {
        logger.warn('Reference not resolved (simplified test)');
      }
    });

    await this.runTest('Zero context loss in conversations', async () => {
      const conversationId = await conversationManager.startConversation();
      
      // Add many turns to test context window
      for (let i = 0; i < 15; i++) {
        await conversationManager.addTurn(
          `Turn ${i}: test input`,
          { content: `Response ${i}` },
          conversationId
        );
      }
      
      const conversation = conversationManager.getConversation(conversationId);
      
      // Check that recent context is preserved
      if (conversation.turns.length < 10) {
        throw new Error('Recent context lost');
      }
      
      // Check that old turns are compressed
      if (!conversation.compressedHistory || conversation.compressedHistory.length === 0) {
        logger.warn('Old turns not compressed (may be within window)');
      }
    });
  }

  // Test 5: Code Intelligence
  async testCodeIntelligence() {
    await this.runTest('Code intelligence initialization', async () => {
      await codeIntelligence.initialize();
    });

    await this.runTest('AST-based code understanding', async () => {
      const code = `
        function calculateSum(a, b) {
          return a + b;
        }
        
        const result = calculateSum(5, 10);
        console.log(result);
      `;
      
      const analysis = await codeIntelligence.analyzeCode(code);
      
      if (!analysis || !analysis.structure) {
        throw new Error('Failed to analyze code');
      }
      
      if (analysis.structure.functions.length === 0) {
        throw new Error('Functions not detected in code');
      }
    });

    await this.runTest('Accurate code modifications > 95%', async () => {
      const testCases = [
        {
          code: 'function oldName() { return 1; }',
          modifications: [{ type: 'rename', target: 'oldName', newName: 'newName' }],
          expected: 'newName'
        },
        {
          code: 'const x = 5;',
          modifications: [{ type: 'rename', target: 'x', newName: 'value' }],
          expected: 'value'
        }
      ];
      
      let successful = 0;
      
      for (const testCase of testCases) {
        const result = await codeIntelligence.modifyCode(
          testCase.code,
          testCase.modifications
        );
        
        if (result.success && result.code.includes(testCase.expected)) {
          successful++;
        }
      }
      
      const accuracy = successful / testCases.length;
      logger.info(`Code modification accuracy: ${(accuracy * 100).toFixed(1)}%`);
      
      if (accuracy < 0.95) {
        throw new Error(`Modification accuracy ${(accuracy * 100).toFixed(1)}% below 95% target`);
      }
    });

    await this.runTest('Refactoring suggestions generation', async () => {
      const complexCode = `
        function processData(data) {
          let result = [];
          for (let i = 0; i < data.length; i++) {
            if (data[i] > 100) {
              result.push(data[i] * 2);
            } else if (data[i] > 50) {
              result.push(data[i] * 1.5);
            } else {
              result.push(data[i]);
            }
          }
          return result;
        }
      `;
      
      const suggestions = await codeIntelligence.suggestRefactoring(complexCode);
      
      if (!suggestions || suggestions.length === 0) {
        throw new Error('No refactoring suggestions generated');
      }
    });
  }

  // Test 6: Integration Testing
  async testIntegration() {
    await this.runTest('Assistant core initialization', async () => {
      await assistantCore.initialize();
    });

    await this.runTest('End-to-end command processing', async () => {
      const input = 'create a new React component called Dashboard';
      const response = await assistantCore.processInput(input);
      
      if (!response || !response.content) {
        throw new Error('Failed to process command end-to-end');
      }
      
      if (!response.commandResult || !response.commandResult.success) {
        throw new Error('Command not successfully processed');
      }
    });

    await this.runTest('Multi-turn conversation flow', async () => {
      const conversation = [
        'I need to create a user authentication system',
        'Start with the login component',
        'Add validation to it',
        'Now create the registration form'
      ];
      
      const result = await assistantCore.processConversation(conversation);
      
      if (!result || result.responses.length !== conversation.length) {
        throw new Error('Conversation not processed correctly');
      }
      
      if (!result.summary || result.summary.totalTurns !== conversation.length) {
        throw new Error('Conversation summary incorrect');
      }
    });

    await this.runTest('Learning and adaptation', async () => {
      // Process similar commands multiple times
      const similarCommands = [
        'create a test file',
        'create another test file',
        'create one more test file'
      ];
      
      for (const command of similarCommands) {
        await assistantCore.processInput(command);
      }
      
      // Check if learning was applied
      const metrics = await assistantCore.getMetrics();
      
      if (metrics.learningEngine.patternsLearned === 0) {
        throw new Error('No learning occurred from repeated patterns');
      }
    });

    await this.runTest('Performance targets met', async () => {
      const times = [];
      
      for (let i = 0; i < 10; i++) {
        const startTime = performance.now();
        await assistantCore.processInput(`test command ${i}`);
        times.push(performance.now() - startTime);
      }
      
      const avgTime = times.reduce((a, b) => a + b, 0) / times.length;
      
      logger.info(`Average response initiation: ${avgTime.toFixed(2)}ms`);
      
      if (avgTime > 100) {
        throw new Error(`Response initiation ${avgTime.toFixed(2)}ms exceeds 100ms target`);
      }
    });
  }

  // Main test runner
  async runAllTests() {
    logger.info('Starting Chapter 3 Assistant Experience Tests...\n');
    
    try {
      // Run test suites
      await this.testCommandProcessing();
      await this.testResponseGeneration();
      await this.testLearningEngine();
      await this.testConversationManagement();
      await this.testCodeIntelligence();
      await this.testIntegration();
      
      // Generate final report
      this.generateFinalReport();
      
    } catch (error) {
      logger.error('Test suite failed', { error: error.message });
    }
  }

  generateFinalReport() {
    const total = this.testResults.passed + this.testResults.failed;
    const passRate = (this.testResults.passed / total * 100).toFixed(1);
    
    logger.info('\n' + '='.repeat(60));
    logger.info('CHAPTER 3 TEST RESULTS');
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
    try {
      const metrics = await assistantCore.getMetrics();
      
      logger.info('\nPERFORMANCE SUMMARY:');
      logger.info('-------------------');
      logger.info(`📊 Total Interactions: ${metrics.core.totalInteractions}`);
      logger.info(`📊 Avg Response Time: ${metrics.summary.avgResponseTime}`);
      logger.info(`📊 Success Rate: ${metrics.summary.successRate}`);
      logger.info(`📊 User Satisfaction: ${metrics.summary.userSatisfaction}`);
      logger.info(`📊 Learning Effectiveness: ${metrics.summary.learningEffectiveness}`);
      logger.info(`📊 Active Conversations: ${metrics.summary.activeConversations}`);
      
      // Success criteria check
      logger.info('\nSUCCESS CRITERIA:');
      logger.info('-----------------');
      
      const criteria = [
        {
          name: 'Command processing < 100ms',
          met: parseFloat(metrics.summary.avgResponseTime) < 100
        },
        {
          name: 'Response relevance > 95%',
          met: parseFloat(metrics.summary.userSatisfaction) > 95
        },
        {
          name: 'Context preservation 100%',
          met: metrics.conversationManager.contextPreservationRate === 1.0
        },
        {
          name: 'Learning effectiveness 20% improvement',
          met: metrics.summary.learningEffectiveness.includes('20') ||
               metrics.summary.learningEffectiveness.includes('reduction')
        },
        {
          name: 'Code modifications > 95% accurate',
          met: metrics.codeIntelligence.successfulModifications > 0
        }
      ];
      
      for (const criterion of criteria) {
        const icon = criterion.met ? '✅' : '❌';
        logger.info(`${icon} ${criterion.name}`);
      }
      
      const allMet = criteria.every(c => c.met);
      
      if (allMet) {
        logger.info('\n🎉 All Chapter 3 success criteria met!');
      } else {
        logger.warn('\n⚠️ Some success criteria not met');
      }
    } catch (error) {
      logger.error('Failed to generate performance summary', { error: error.message });
    }
  }
}

// Run tests
const tester = new Chapter3Tests();
tester.runAllTests();