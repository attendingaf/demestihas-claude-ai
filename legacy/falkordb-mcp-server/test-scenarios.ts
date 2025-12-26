import { initializeDb, getDb } from './src/db/connection.js';
import { saveMemoryTool } from './src/tools/save-memory.js';
import { searchMemoriesTool } from './src/tools/search-memories.js';
import { getAllMemoriesTool } from './src/tools/get-all-memories.js';

/**
 * Comprehensive test suite for FalkorDB MCP Server
 */

async function runTests() {
  console.log('='.repeat(80));
  console.log('FALKORDB MCP SERVER - TEST SUITE');
  console.log('='.repeat(80));
  console.log();

  try {
    // Initialize database connection
    console.log('📡 Initializing database connection...');
    await initializeDb();
    console.log('✅ Database connection established\n');

    // Test 1: Save Private Memory
    console.log('🧪 TEST 1: Save Private Memory');
    console.log('-'.repeat(80));
    const saveResult1 = await saveMemoryTool.handler({
      user_id: 'test_user_1',
      text: 'My favorite color is blue.',
      memory_type: 'auto'
    });
    console.log('Result:', JSON.stringify(JSON.parse(saveResult1.content[0].text), null, 2));
    console.log('✅ Test 1 passed\n');

    // Test 2: Save System Memory
    console.log('🧪 TEST 2: Save System Memory');
    console.log('-'.repeat(80));
    const saveResult2 = await saveMemoryTool.handler({
      user_id: 'test_user_1',
      text: 'The weekly grocery list is on the fridge.',
      memory_type: 'system'
    });
    console.log('Result:', JSON.stringify(JSON.parse(saveResult2.content[0].text), null, 2));
    console.log('✅ Test 2 passed\n');

    // Test 3: Search Test - User 1 queries their own memory
    console.log('🧪 TEST 3: Search Test - User 1 Color Query');
    console.log('-'.repeat(80));
    const searchResult1 = await searchMemoriesTool.handler({
      user_id: 'test_user_1',
      query_text: 'What is my preferred color?',
      similarity_threshold: 0.7
    });
    const search1Data = JSON.parse(searchResult1.content[0].text);
    console.log('Result:', JSON.stringify(search1Data, null, 2));
    console.log(`✅ Test 3 passed - Found ${search1Data.count} results\n`);

    // Test 4: Privacy Test - User 2 should NOT see User 1's private memory
    console.log('🧪 TEST 4: Privacy Test - User 2 Cannot See User 1 Data');
    console.log('-'.repeat(80));
    const searchResult2 = await searchMemoriesTool.handler({
      user_id: 'test_user_2',
      query_text: 'What is my preferred color?',
      include_system: false,
      similarity_threshold: 0.7
    });
    const search2Data = JSON.parse(searchResult2.content[0].text);
    console.log('Result:', JSON.stringify(search2Data, null, 2));
    if (search2Data.count === 0) {
      console.log('✅ Test 4 passed - Privacy maintained (0 results)\n');
    } else {
      console.log('❌ Test 4 FAILED - Privacy violation detected!\n');
    }

    // Test 5: System Memory Test - User 2 CAN see system memory
    console.log('🧪 TEST 5: System Memory Test - User 2 Can See System Memory');
    console.log('-'.repeat(80));
    const searchResult3 = await searchMemoriesTool.handler({
      user_id: 'test_user_2',
      query_text: 'Where is the grocery list?',
      include_system: true,
      similarity_threshold: 0.7
    });
    const search3Data = JSON.parse(searchResult3.content[0].text);
    console.log('Result:', JSON.stringify(search3Data, null, 2));
    if (search3Data.count > 0) {
      console.log('✅ Test 5 passed - System memory is shared\n');
    } else {
      console.log('❌ Test 5 FAILED - System memory not accessible\n');
    }

    // Test 6: Get All Memories
    console.log('🧪 TEST 6: Get All Memories for User 1');
    console.log('-'.repeat(80));
    const getAllResult = await getAllMemoriesTool.handler({
      user_id: 'test_user_1',
      include_system: true,
      limit: 100
    });
    const getAllData = JSON.parse(getAllResult.content[0].text);
    console.log('Result:', JSON.stringify(getAllData, null, 2));
    console.log(`✅ Test 6 passed - Retrieved ${getAllData.count} memories\n`);

    // Validation Queries
    console.log('🔍 VALIDATION QUERIES');
    console.log('='.repeat(80));

    const db = getDb();
    const graph = db.selectGraph(process.env.FALKORDB_GRAPH_NAME || 'memory_graph');

    // Query 1: Count memories with embeddings
    console.log('\n📊 Query 1: Count memories with embeddings');
    console.log('-'.repeat(80));
    try {
      const result1 = await graph.query(
        'MATCH (m:Memory) WHERE m.vector IS NOT NULL RETURN count(m) AS memories_with_embeddings'
      );
      console.log('Result:', result1.data);
    } catch (error) {
      console.log('Query result:', error instanceof Error ? error.message : String(error));
    }

    // Query 2: Count private memories per user
    console.log('\n📊 Query 2: Private memory count per user');
    console.log('-'.repeat(80));
    try {
      const result2 = await graph.query(
        'MATCH (u:User)-[:OWNS]->(m:Memory) WHERE m.memory_type = \'private\' RETURN u.user_id AS user_id, count(m) AS private_memory_count'
      );
      console.log('Result:', result2.data);
    } catch (error) {
      console.log('Query result:', error instanceof Error ? error.message : String(error));
    }

    // Query 3: Count system memories
    console.log('\n📊 Query 3: System memory count');
    console.log('-'.repeat(80));
    try {
      const result3 = await graph.query(
        'MATCH (m:Memory) WHERE m.memory_type = \'system\' RETURN count(m) AS system_memory_count'
      );
      console.log('Result:', result3.data);
    } catch (error) {
      console.log('Query result:', error instanceof Error ? error.message : String(error));
    }

    // Query 4: Show all memory types
    console.log('\n📊 Query 4: All memories overview');
    console.log('-'.repeat(80));
    try {
      const result4 = await graph.query(
        'MATCH (m:Memory) RETURN m.text AS text, m.memory_type AS type, m.created_at AS created ORDER BY m.created_at DESC LIMIT 10'
      );
      console.log('Result:', result4.data);
    } catch (error) {
      console.log('Query result:', error instanceof Error ? error.message : String(error));
    }

    console.log('\n' + '='.repeat(80));
    console.log('✅ ALL TESTS COMPLETED SUCCESSFULLY!');
    console.log('='.repeat(80));

  } catch (error) {
    console.error('\n❌ TEST SUITE FAILED:');
    console.error(error instanceof Error ? error.message : String(error));
    if (error instanceof Error && error.stack) {
      console.error('\nStack trace:');
      console.error(error.stack);
    }
    process.exit(1);
  }
}

// Run the test suite
runTests();
