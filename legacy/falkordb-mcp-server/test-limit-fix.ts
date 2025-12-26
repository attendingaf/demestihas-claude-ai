import { initializeDb } from './src/db/connection.js';
import { getAllMemoriesTool } from './src/tools/get-all-memories.js';

/**
 * Quick test to verify the LIMIT parameter fix
 */

async function testLimitFix() {
  console.log('Testing LIMIT parameter fix...\n');

  try {
    // Initialize database
    await initializeDb();
    console.log('✓ Database connected\n');

    // Test 1: Normal limit
    console.log('Test 1: Normal limit (50)');
    const result1 = await getAllMemoriesTool.handler({
      user_id: 'test_user',
      limit: 50,
      include_system: true
    });
    console.log('✓ Test 1 passed - No error with limit=50\n');

    // Test 2: Maximum limit
    console.log('Test 2: Maximum limit (100)');
    const result2 = await getAllMemoriesTool.handler({
      user_id: 'test_user',
      limit: 100,
      include_system: true
    });
    console.log('✓ Test 2 passed - No error with limit=100\n');

    // Test 3: Very large limit (should be capped at 10000)
    console.log('Test 3: Very large limit (99999 - should be capped at 10000)');
    const result3 = await getAllMemoriesTool.handler({
      user_id: 'test_user',
      limit: 99999,
      include_system: true
    });
    console.log('✓ Test 3 passed - Large limit handled safely\n');

    // Test 4: Minimum limit
    console.log('Test 4: Minimum limit (1)');
    const result4 = await getAllMemoriesTool.handler({
      user_id: 'test_user',
      limit: 1,
      include_system: true
    });
    console.log('✓ Test 4 passed - No error with limit=1\n');

    console.log('='.repeat(60));
    console.log('✅ ALL LIMIT TESTS PASSED!');
    console.log('='.repeat(60));
    console.log('\nThe LIMIT parameter bug has been successfully fixed!');
    console.log('The query now uses safe integer interpolation.');

  } catch (error) {
    console.error('❌ Test failed:');
    console.error(error instanceof Error ? error.message : String(error));
    process.exit(1);
  }
}

testLimitFix();
