#!/usr/bin/env node

/**
 * Test the complete memory integration
 */

const SmartMemoryClient = require('./smart-memory-client.js');

async function testMemoryIntegration() {
  console.log('Testing Smart Memory Integration...');
  
  const memory = new SmartMemoryClient();
  
  try {
    // Test health check
    console.log('\n1. Testing health check...');
    const isHealthy = await memory.isHealthy();
    console.log(`Memory API healthy: ${isHealthy}`);
    
    if (!isHealthy) {
      console.error('Memory API is not healthy. Make sure the server is running.');
      return;
    }
    
    // Test storing a memory
    console.log('\n2. Testing memory storage...');
    const storeResult = await memory.set('test_key_123', 'Test value from SmartMemoryClient', {
      type: 'integration_test',
      importance: 'high',
      category: 'testing'
    });
    console.log('Store result:', storeResult);
    
    // Test retrieving the memory
    console.log('\n3. Testing memory retrieval...');
    const retrievedValue = await memory.get('test_key_123');
    console.log('Retrieved value:', retrievedValue);
    
    // Test search functionality
    console.log('\n4. Testing memory search...');
    const searchResults = await memory.search('integration test');
    console.log('Search results:', searchResults);
    
    // Test getting all entries
    console.log('\n5. Testing entries retrieval...');
    const entries = await memory.entries();
    console.log(`Total entries: ${entries.length}`);
    console.log('Sample entries:', entries.slice(0, 3));
    
    // Test size
    console.log('\n6. Testing memory size...');
    const size = await memory.size();
    console.log(`Memory size: ${size}`);
    
    // Test persist
    console.log('\n7. Testing persist...');
    const persistResult = await memory.persist();
    console.log('Persist result:', persistResult);
    
    console.log('\n✅ All tests completed successfully!');
    
  } catch (error) {
    console.error('\n❌ Test failed:', error);
  }
}

// Run the test
testMemoryIntegration();