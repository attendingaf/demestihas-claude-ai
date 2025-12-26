#!/usr/bin/env node

/**
 * Test EA-AI bootstrap system with new memory integration
 */

const EABootstrap = require('./bootstrap.js');

async function testEAAIMemory() {
  console.log('Testing EA-AI Bootstrap with Smart Memory...');
  
  try {
    // Initialize EA-AI system
    console.log('\n1. Initializing EA-AI Bootstrap...');
    const initResult = await EABootstrap.init({
      maxLatency: 300,
      fallbackEnabled: true,
      memoryShare: true
    });
    
    console.log('Bootstrap result:', initResult);
    
    // Test memory operations
    console.log('\n2. Testing memory operations...');
    
    // Store a test memory
    await EABootstrap.memory.set('ea_test_key', 'EA-AI test value', {
      type: 'ea_ai_test',
      importance: 'medium'
    });
    console.log('Stored test memory');
    
    // Retrieve the memory
    const retrievedValue = await EABootstrap.memory.get('ea_test_key');
    console.log('Retrieved value:', retrievedValue);
    
    // Test memory size
    const memorySize = await EABootstrap.memory.size();
    console.log('Memory size:', memorySize);
    
    // Test search
    const searchResults = await EABootstrap.memory.search('EA-AI');
    console.log('Search results:', searchResults.length, 'items found');
    
    // Test persistence
    console.log('\n3. Testing memory persistence...');
    const persistResult = await EABootstrap.persistMemory();
    console.log('Persist result:', persistResult);
    
    // Update memory
    console.log('\n4. Testing memory updates...');
    await EABootstrap.updateMemory({
      'test_update': 'Updated value from EA-AI',
      persist: true
    });
    console.log('Memory updated');
    
    console.log('\n✅ EA-AI Memory integration test completed successfully!');
    
  } catch (error) {
    console.error('\n❌ EA-AI Memory test failed:', error);
  }
}

// Run the test
testEAAIMemory();