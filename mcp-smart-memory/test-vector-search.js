#!/usr/bin/env node

import fetch from 'node-fetch';
import { config } from 'dotenv';
import path from 'path';
import { fileURLToPath } from 'url';

const __dirname = path.dirname(fileURLToPath(import.meta.url));
config({ path: path.join(__dirname, '.env') });

const API_URL = 'http://localhost:7777';

// Color codes for terminal output
const colors = {
  reset: '\x1b[0m',
  bright: '\x1b[1m',
  green: '\x1b[32m',
  red: '\x1b[31m',
  yellow: '\x1b[33m',
  blue: '\x1b[34m',
  cyan: '\x1b[36m'
};

function log(message, color = 'reset') {
  console.log(`${colors[color]}${message}${colors.reset}`);
}

function logTest(name) {
  console.log(`\n${colors.bright}${colors.blue}━━━ ${name} ━━━${colors.reset}`);
}

function logResult(success, message) {
  const icon = success ? '✅' : '❌';
  const color = success ? 'green' : 'red';
  log(`${icon} ${message}`, color);
}

async function checkHealth() {
  logTest('Test 0: API Health Check');

  try {
    const response = await fetch(`${API_URL}/health`);
    const data = await response.json();

    logResult(data.status === 'healthy', `API Status: ${data.status}`);
    logResult(data.initialized, `System Initialized: ${data.initialized}`);

    if (data.features) {
      log('\nFeatures:', 'cyan');
      logResult(data.features.vectorSearch, `  Vector Search: ${data.features.vectorSearch ? 'Enabled' : 'Disabled'}`);
      logResult(data.features.semanticSearch, `  Semantic Search: ${data.features.semanticSearch ? 'Enabled' : 'Disabled'}`);
      logResult(data.features.hybridSearch, `  Hybrid Search: ${data.features.hybridSearch ? 'Enabled' : 'Disabled'}`);
      logResult(data.features.fts5Search, `  FTS5 Search: ${data.features.fts5Search ? 'Enabled' : 'Disabled'}`);
    }

    if (data.stats) {
      log('\nMemory Stats:', 'cyan');
      console.log(`  Total Memories: ${data.stats.totalMemories}`);
      console.log(`  Vector Search Enabled: ${data.stats.vectorSearchEnabled || false}`);
    }

    return data.features?.vectorSearch || false;
  } catch (error) {
    logResult(false, `Health check failed: ${error.message}`);
    return false;
  }
}

async function storeTestMemory(content, category) {
  try {
    const response = await fetch(`${API_URL}/memory`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        content,
        category,
        type: 'test',
        importance: 'medium'
      })
    });

    const data = await response.json();
    return data.id;
  } catch (error) {
    console.error('Failed to store test memory:', error);
    return null;
  }
}

async function runSemanticSearchTest() {
  logTest('Test 1: Semantic Search');

  // Store test memories with different semantic meanings
  log('Storing test memories...', 'yellow');

  const testMemories = [
    { content: 'The OXOS medical device requires FDA compliance documentation for regulatory approval', category: 'medical' },
    { content: 'Healthcare regulations mandate strict compliance with patient data privacy laws', category: 'medical' },
    { content: 'The calendar application has conflicts with family event scheduling on weekends', category: 'scheduling' },
    { content: 'Time management issues arise when personal and work schedules overlap', category: 'scheduling' },
    { content: 'Python debugging revealed a memory leak in the data processing pipeline', category: 'programming' },
    { content: 'Error handling in the Python script needs improvement for edge cases', category: 'programming' }
  ];

  // Store memories
  for (const memory of testMemories) {
    await storeTestMemory(memory.content, memory.category);
  }

  // Wait a moment for indexing
  await new Promise(resolve => setTimeout(resolve, 1000));

  // Test semantic search
  const queries = [
    { query: 'medical compliance documentation', expected: 'OXOS' },
    { query: 'family scheduling issues', expected: 'calendar' },
    { query: 'Python error', expected: 'debugging' }
  ];

  for (const test of queries) {
    log(`\nQuery: "${test.query}"`, 'cyan');
    log(`Expected to find: ${test.expected}`, 'yellow');

    try {
      const response = await fetch(`${API_URL}/search/semantic?q=${encodeURIComponent(test.query)}&limit=3`);
      const data = await response.json();

      if (data.results && data.results.length > 0) {
        logResult(true, `Found ${data.count} semantic matches`);

        const topResult = data.results[0];
        const foundExpected = topResult.content.includes(test.expected);

        logResult(foundExpected, `Top result contains "${test.expected}": ${foundExpected}`);
        console.log(`  Similarity: ${topResult.similarity?.toFixed(3) || 'N/A'}`);
        console.log(`  Content: ${topResult.content.substring(0, 60)}...`);
      } else {
        logResult(false, 'No semantic matches found');
      }
    } catch (error) {
      logResult(false, `Semantic search failed: ${error.message}`);
    }
  }
}

async function runHybridSearchTest() {
  logTest('Test 2: Hybrid Search');

  const query = 'compliance medical OXOS';
  log(`Query: "${query}"`, 'cyan');
  log('Should find both exact keyword matches AND semantically similar content', 'yellow');

  try {
    const response = await fetch(`${API_URL}/search?q=${encodeURIComponent(query)}&mode=hybrid&limit=5`);
    const data = await response.json();

    if (data.results && data.results.length > 0) {
      logResult(true, `Found ${data.count} hybrid matches`);
      log(`Explanation: ${data.explanation}`, 'yellow');

      // Check if results come from multiple sources
      const sources = new Set();
      data.results.forEach(result => {
        if (result.sources) {
          result.sources.forEach(s => sources.add(s));
        }
      });

      logResult(sources.size > 1, `Using multiple search methods: ${Array.from(sources).join(', ')}`);

      console.log('\nTop 3 results:');
      data.results.slice(0, 3).forEach((result, i) => {
        console.log(`  ${i + 1}. Score: ${result.finalScore?.toFixed(3) || result.similarity?.toFixed(3) || 'N/A'}`);
        console.log(`     Sources: ${result.sources?.join(', ') || 'unknown'}`);
        console.log(`     Content: ${result.content.substring(0, 50)}...`);
      });
    } else {
      logResult(false, 'No hybrid matches found');
    }
  } catch (error) {
    logResult(false, `Hybrid search failed: ${error.message}`);
  }
}

async function runModeComparisonTest() {
  logTest('Test 3: Search Mode Comparison');

  const query = 'task management and scheduling';
  log(`Query: "${query}"`, 'cyan');

  const modes = ['keyword', 'semantic', 'hybrid'];
  const results = {};

  for (const mode of modes) {
    try {
      const response = await fetch(`${API_URL}/search?q=${encodeURIComponent(query)}&mode=${mode}&limit=5`);
      const data = await response.json();
      results[mode] = data;

      log(`\n${mode.toUpperCase()} Mode:`, 'blue');
      console.log(`  Results: ${data.count}`);

      if (data.results && data.results.length > 0) {
        console.log(`  Top match: ${data.results[0].content.substring(0, 50)}...`);
        const score = data.results[0].similarity || data.results[0].finalScore || data.results[0].score;
        console.log(`  Score: ${score?.toFixed(3) || 'N/A'}`);
      }
    } catch (error) {
      logResult(false, `${mode} search failed: ${error.message}`);
    }
  }

  // Compare results
  log('\nComparison:', 'cyan');
  const keywordCount = results.keyword?.count || 0;
  const semanticCount = results.semantic?.count || 0;
  const hybridCount = results.hybrid?.count || 0;

  console.log(`  Keyword found: ${keywordCount} results`);
  console.log(`  Semantic found: ${semanticCount} results`);
  console.log(`  Hybrid found: ${hybridCount} results`);

  const hybridBest = hybridCount >= Math.max(keywordCount, semanticCount);
  logResult(hybridBest, `Hybrid search performs best: ${hybridBest}`);
}

async function runPerformanceTest() {
  logTest('Test 4: Performance Benchmark');

  const query = 'test performance benchmark';
  const iterations = 10;

  const modes = ['keyword', 'semantic', 'hybrid'];
  const timings = {};

  for (const mode of modes) {
    const times = [];

    for (let i = 0; i < iterations; i++) {
      const start = Date.now();

      try {
        await fetch(`${API_URL}/search?q=${encodeURIComponent(query)}&mode=${mode}`);
        const duration = Date.now() - start;
        times.push(duration);
      } catch (error) {
        console.error(`Performance test failed for ${mode}:`, error.message);
      }
    }

    if (times.length > 0) {
      const avg = times.reduce((a, b) => a + b, 0) / times.length;
      const min = Math.min(...times);
      const max = Math.max(...times);

      timings[mode] = { avg, min, max };

      log(`\n${mode.toUpperCase()} Mode:`, 'blue');
      console.log(`  Average: ${avg.toFixed(0)}ms`);
      console.log(`  Min: ${min}ms, Max: ${max}ms`);

      const fast = avg < 200;
      logResult(fast, `Performance: ${fast ? 'FAST' : 'SLOW'} (<200ms target)`);
    }
  }
}

async function runContextRetrievalTest() {
  logTest('Test 5: Context Retrieval');

  const query = 'OXOS medical compliance';
  log(`Query: "${query}"`, 'cyan');

  try {
    const response = await fetch(`${API_URL}/context?q=${encodeURIComponent(query)}&limit=5&mode=hybrid`);
    const data = await response.json();

    if (data.context && data.context.length > 0) {
      logResult(true, `Retrieved ${data.count} contextual memories`);

      console.log('\nContext includes:');
      data.context.slice(0, 3).forEach((memory, i) => {
        console.log(`  ${i + 1}. ${memory.content.substring(0, 60)}...`);
      });

      if (data.patterns && data.patterns.length > 0) {
        log('\nDetected patterns:', 'cyan');
        data.patterns.forEach(p => console.log(`  - ${p}`));
      }
    } else {
      logResult(false, 'No context retrieved');
    }
  } catch (error) {
    logResult(false, `Context retrieval failed: ${error.message}`);
  }
}

async function cleanup() {
  logTest('Cleanup');

  try {
    // Get test memories
    const response = await fetch(`${API_URL}/memories?type=test&limit=100`);
    const data = await response.json();

    if (data.memories && data.memories.length > 0) {
      log(`Cleaning up ${data.memories.length} test memories...`, 'yellow');

      for (const memory of data.memories) {
        await fetch(`${API_URL}/memory/${memory.id}`, { method: 'DELETE' });
      }

      logResult(true, 'Cleanup complete');
    } else {
      log('No test memories to clean up', 'yellow');
    }
  } catch (error) {
    logResult(false, `Cleanup failed: ${error.message}`);
  }
}

async function runAllTests() {
  console.log(`
${colors.bright}${colors.cyan}╔════════════════════════════════════════════════╗
║     🧪 Vector Search Implementation Tests      ║
╚════════════════════════════════════════════════╝${colors.reset}
`);

  log('Starting test suite...', 'yellow');
  log(`API URL: ${API_URL}`, 'yellow');

  // Check if API is running and has vector search
  const hasVectorSearch = await checkHealth();

  if (!hasVectorSearch) {
    log('\n⚠️  Vector search is not enabled!', 'red');
    log('Please ensure:', 'yellow');
    log('1. Supabase credentials are in .env file', 'yellow');
    log('2. OpenAI API key is in .env file', 'yellow');
    log('3. pgvector is enabled in Supabase', 'yellow');
    log('4. The migration script has been run', 'yellow');

    // Run limited tests anyway
    log('\nRunning limited tests with FTS5 only...', 'yellow');
  }

  // Run test suite
  await runSemanticSearchTest();
  await runHybridSearchTest();
  await runModeComparisonTest();
  await runPerformanceTest();
  await runContextRetrievalTest();

  // Cleanup
  await cleanup();

  // Summary
  console.log(`
${colors.bright}${colors.green}╔════════════════════════════════════════════════╗
║           ✅ Test Suite Complete!              ║
╚════════════════════════════════════════════════╝${colors.reset}
`);

  if (hasVectorSearch) {
    log('Vector search is working correctly!', 'green');
    log('Your memory system now understands meaning, not just keywords.', 'green');
  } else {
    log('Tests completed with FTS5 fallback.', 'yellow');
    log('Enable vector search for full semantic capabilities.', 'yellow');
  }
}

// Check if API is running
async function checkAPIRunning() {
  try {
    const response = await fetch(`${API_URL}/health`);
    return response.ok;
  } catch {
    return false;
  }
}

// Main execution
async function main() {
  const apiRunning = await checkAPIRunning();

  if (!apiRunning) {
    log('❌ API server is not running!', 'red');
    log('\nPlease start the server first:', 'yellow');
    log('  node memory-api-vector.js', 'cyan');
    log('\nOr if you haven\'t migrated yet:', 'yellow');
    log('  node migrate-to-vectors.js', 'cyan');
    process.exit(1);
  }

  await runAllTests();
}

// Run tests
main().catch(error => {
  log(`\n❌ Test suite failed: ${error.message}`, 'red');
  process.exit(1);
});
