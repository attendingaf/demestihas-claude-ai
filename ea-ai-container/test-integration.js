#!/usr/bin/env node

/**
 * Integration test for EA-AI containerized agent
 */

const EAAIBridge = require('./claude-integration');

async function runTests() {
  console.log('🧪 Testing EA-AI Container Integration...\n');

  const bridge = new EAAIBridge();
  let passed = 0;
  let failed = 0;

  // Test 1: Health Check
  console.log('1. Testing health check...');
  try {
    const health = await bridge.health();
    if (health.status === 'healthy' && health.agents.length === 4) {
      console.log('   ✅ Health check passed');
      passed++;
    } else {
      throw new Error('Invalid health response');
    }
  } catch (error) {
    console.log(`   ❌ Health check failed: ${error.message}`);
    failed++;
  }

  // Test 2: Memory Operations
  console.log('\n2. Testing memory operations...');
  try {
    // Set memory
    await bridge.memory('set', 'test_key', 'test_value', { type: 'test' });

    // Get memory
    const result = await bridge.memory('get', 'test_key');
    if (result.data && result.data.value === 'test_value') {
      console.log('   ✅ Memory set/get passed');
      passed++;
    } else {
      throw new Error('Memory value mismatch');
    }
  } catch (error) {
    console.log(`   ❌ Memory operations failed: ${error.message}`);
    failed++;
  }

  // Test 3: Agent Routing
  console.log('\n3. Testing agent routing...');
  try {
    const emailRoute = await bridge.route('auto', 'draft an email to decline a meeting');
    if (emailRoute.agent === 'pluma') {
      console.log('   ✅ Email routing passed (routed to Pluma)');
      passed++;
    } else {
      throw new Error(`Expected Pluma, got ${emailRoute.agent}`);
    }

    const calendarRoute = await bridge.route('auto', 'schedule a meeting for tomorrow');
    if (calendarRoute.agent === 'huata') {
      console.log('   ✅ Calendar routing passed (routed to Huata)');
      passed++;
    } else {
      throw new Error(`Expected Huata, got ${calendarRoute.agent}`);
    }

    const taskRoute = await bridge.route('auto', 'break down this complex project');
    if (taskRoute.agent === 'lyco') {
      console.log('   ✅ Task routing passed (routed to Lyco)');
      passed++;
    } else {
      throw new Error(`Expected Lyco, got ${taskRoute.agent}`);
    }
  } catch (error) {
    console.log(`   ❌ Agent routing failed: ${error.message}`);
    failed += 3;
  }

  // Test 4: Family Context
  console.log('\n4. Testing family context...');
  try {
    const meneContext = await bridge.family('mene');
    if (meneContext.data && meneContext.data.preferences) {
      console.log('   ✅ Family context (Mene) passed');
      passed++;
    } else {
      throw new Error('Invalid Mene context');
    }

    const allContext = await bridge.family('auto');
    if (allContext.context && allContext.context.mene && allContext.context.cindy) {
      console.log('   ✅ Family context (all) passed');
      passed++;
    } else {
      throw new Error('Invalid family context');
    }
  } catch (error) {
    console.log(`   ❌ Family context failed: ${error.message}`);
    failed += 2;
  }

  // Test 5: ADHD Task Management
  console.log('\n5. Testing ADHD task management...');
  try {
    const breakdown = await bridge.taskADHD('break_down', 'prepare quarterly presentation with financial analysis and market trends');
    if (breakdown.chunks && breakdown.chunks.length > 0) {
      console.log('   ✅ Task breakdown passed');
      console.log(`      Created ${breakdown.chunks.length} chunks`);
      passed++;
    } else {
      throw new Error('No chunks created');
    }

    const priority = await bridge.taskADHD('prioritize', 'urgent report due today');
    if (priority.priority === 'urgent') {
      console.log('   ✅ Task prioritization passed');
      passed++;
    } else {
      throw new Error(`Expected urgent priority, got ${priority.priority}`);
    }

    const energy = await bridge.taskADHD('energy_match', 'complex analysis task');
    if (energy.current_energy) {
      console.log('   ✅ Energy matching passed');
      console.log(`      Current energy: ${energy.current_energy}`);
      passed++;
    } else {
      throw new Error('No energy level returned');
    }
  } catch (error) {
    console.log(`   ❌ ADHD task management failed: ${error.message}`);
    failed += 3;
  }

  // Test 6: Memory Persistence
  console.log('\n6. Testing memory persistence...');
  try {
    await bridge.memory('set', 'persist_test', 'should persist', { importance: 'high' });
    const persistResult = await bridge.memory('persist');
    if (persistResult.persisted > 0) {
      console.log('   ✅ Memory persistence passed');
      passed++;
    } else {
      throw new Error('No items persisted');
    }
  } catch (error) {
    console.log(`   ❌ Memory persistence failed: ${error.message}`);
    failed++;
  }

  // Test 7: Memory Search
  console.log('\n7. Testing memory search...');
  try {
    await bridge.memory('set', 'search_test_1', 'ea-ai integration test');
    await bridge.memory('set', 'search_test_2', 'ea-ai memory system');
    const searchResult = await bridge.memory('search', 'ea-ai');
    if (searchResult.results && searchResult.results.length >= 2) {
      console.log('   ✅ Memory search passed');
      console.log(`      Found ${searchResult.results.length} matching items`);
      passed++;
    } else {
      throw new Error('Search did not find expected items');
    }
  } catch (error) {
    console.log(`   ❌ Memory search failed: ${error.message}`);
    failed++;
  }

  // Summary
  console.log('\n' + '='.repeat(50));
  console.log('📊 Test Summary:');
  console.log(`   Passed: ${passed}`);
  console.log(`   Failed: ${failed}`);
  console.log(`   Total:  ${passed + failed}`);
  console.log('='.repeat(50));

  if (failed === 0) {
    console.log('\n🎉 All tests passed! EA-AI container is ready for deployment.');
    process.exit(0);
  } else {
    console.log('\n⚠️  Some tests failed. Please check the container logs.');
    process.exit(1);
  }
}

// Run tests if container is up
const checkContainer = async () => {
  const bridge = new EAAIBridge();
  let attempts = 0;
  const maxAttempts = 5;

  console.log('Waiting for container to be ready...');

  while (attempts < maxAttempts) {
    try {
      const health = await bridge.health();
      if (health.status === 'healthy') {
        console.log('Container is ready!\n');
        return true;
      }
    } catch (error) {
      // Container not ready yet
    }

    attempts++;
    if (attempts < maxAttempts) {
      process.stdout.write('.');
      await new Promise(resolve => setTimeout(resolve, 2000));
    }
  }

  console.log('\n❌ Container is not responding. Please ensure it is running:');
  console.log('   docker-compose up -d');
  return false;
};

// Main execution
(async () => {
  const isReady = await checkContainer();
  if (isReady) {
    await runTests();
  } else {
    process.exit(1);
  }
})();
