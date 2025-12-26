#!/usr/bin/env node

/**
 * Test memory system performance requirements
 * Target: <100ms retrieval
 */

const SmartMemoryClient = require('./smart-memory-client.js');

async function testPerformance() {
  console.log('Testing Memory Performance Requirements...');
  
  const memory = new SmartMemoryClient();
  
  try {
    // Store several test memories for performance testing
    console.log('\n1. Setting up test data...');
    const testData = [
      { key: 'perf_test_1', value: 'Performance test memory 1', type: 'test' },
      { key: 'perf_test_2', value: 'Performance test memory 2', type: 'test' },
      { key: 'perf_test_3', value: 'Performance test memory 3', type: 'test' },
      { key: 'perf_test_4', value: 'Performance test memory 4', type: 'test' },
      { key: 'perf_test_5', value: 'Performance test memory 5', type: 'test' }
    ];
    
    for (const item of testData) {
      await memory.set(item.key, item.value, { type: item.type });
    }
    console.log('Test data stored successfully');
    
    // Test individual retrieval performance
    console.log('\n2. Testing individual retrieval performance...');
    const retrievalTimes = [];
    
    for (let i = 0; i < 10; i++) {
      const start = Date.now();
      const result = await memory.get('perf_test_1');
      const duration = Date.now() - start;
      retrievalTimes.push(duration);
      console.log(`Retrieval ${i + 1}: ${duration}ms (${result ? 'success' : 'failed'})`);
    }
    
    const avgRetrieval = retrievalTimes.reduce((a, b) => a + b, 0) / retrievalTimes.length;
    const maxRetrieval = Math.max(...retrievalTimes);
    const minRetrieval = Math.min(...retrievalTimes);
    
    console.log(`\nRetrieval Performance:`);
    console.log(`  Average: ${avgRetrieval.toFixed(2)}ms`);
    console.log(`  Minimum: ${minRetrieval}ms`);
    console.log(`  Maximum: ${maxRetrieval}ms`);
    console.log(`  Target: <100ms`);
    console.log(`  Status: ${maxRetrieval < 100 ? '✅ PASS' : '❌ FAIL'}`);
    
    // Test search performance
    console.log('\n3. Testing search performance...');
    const searchTimes = [];
    
    for (let i = 0; i < 5; i++) {
      const start = Date.now();
      const results = await memory.search('performance test');
      const duration = Date.now() - start;
      searchTimes.push(duration);
      console.log(`Search ${i + 1}: ${duration}ms (${results.length} results)`);
    }
    
    const avgSearch = searchTimes.reduce((a, b) => a + b, 0) / searchTimes.length;
    const maxSearch = Math.max(...searchTimes);
    const minSearch = Math.min(...searchTimes);
    
    console.log(`\nSearch Performance:`);
    console.log(`  Average: ${avgSearch.toFixed(2)}ms`);
    console.log(`  Minimum: ${minSearch}ms`);
    console.log(`  Maximum: ${maxSearch}ms`);
    console.log(`  Target: <100ms`);
    console.log(`  Status: ${maxSearch < 100 ? '✅ PASS' : '❌ FAIL'}`);
    
    // Test concurrent operations
    console.log('\n4. Testing concurrent operations...');
    const concurrentStart = Date.now();
    
    const promises = [
      memory.get('perf_test_1'),
      memory.get('perf_test_2'),
      memory.search('performance'),
      memory.size(),
      memory.get('perf_test_3')
    ];
    
    const results = await Promise.all(promises);
    const concurrentDuration = Date.now() - concurrentStart;
    
    console.log(`Concurrent operations: ${concurrentDuration}ms`);
    console.log(`Results: ${results.map(r => r ? 'success' : 'failed').join(', ')}`);
    console.log(`Status: ${concurrentDuration < 200 ? '✅ PASS' : '❌ FAIL'} (target <200ms for 5 operations)`);
    
    // Overall assessment
    console.log('\n5. Performance Summary:');
    const overallPass = maxRetrieval < 100 && maxSearch < 100 && concurrentDuration < 200;
    console.log(`Overall Performance: ${overallPass ? '✅ MEETS REQUIREMENTS' : '❌ NEEDS OPTIMIZATION'}`);
    
    console.log('\nDetailed Analysis:');
    console.log(`- Single retrieval: ${avgRetrieval.toFixed(2)}ms avg (target: <100ms)`);
    console.log(`- Search operations: ${avgSearch.toFixed(2)}ms avg (target: <100ms)`);
    console.log(`- Concurrent ops: ${concurrentDuration}ms for 5 operations`);
    console.log(`- Memory backend: Simple SQLite with FTS5`);
    
  } catch (error) {
    console.error('\n❌ Performance test failed:', error);
  }
}

// Run the performance test
testPerformance();