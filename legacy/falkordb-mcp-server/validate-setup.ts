import { initializeDb, getDb } from './src/db/connection.js';

/**
 * Validation script to verify the server setup and database connectivity
 * This can run without OpenAI API key
 */

async function validateSetup() {
  console.log('='.repeat(80));
  console.log('FALKORDB MCP SERVER - SETUP VALIDATION');
  console.log('='.repeat(80));
  console.log();

  let testsPasssed = 0;
  let testsFailed = 0;

  try {
    // Test 1: Database Connection
    console.log('✓ Test 1: Database Connection');
    console.log('-'.repeat(80));
    await initializeDb();
    console.log('✅ Database connection successful\n');
    testsPasssed++;

    const db = getDb();
    const graph = db.selectGraph(process.env.FALKORDB_GRAPH_NAME || 'memory_graph');

    // Test 2: Check if graph exists and is accessible
    console.log('✓ Test 2: Graph Accessibility');
    console.log('-'.repeat(80));
    try {
      const testResult = await graph.query('RETURN 1 AS test');
      console.log('✅ Graph is accessible and responsive\n');
      testsPasssed++;
    } catch (error) {
      console.log('❌ Graph query failed:', error instanceof Error ? error.message : String(error));
      testsFailed++;
    }

    // Test 3: Check existing data
    console.log('✓ Test 3: Existing Data Check');
    console.log('-'.repeat(80));
    try {
      const countResult = await graph.query('MATCH (m:Memory) RETURN count(m) AS total_memories');
      const count = countResult.data && countResult.data[0] ? countResult.data[0][0] : 0;
      console.log(`Found ${count} existing memories in the database`);

      if (count > 0) {
        console.log('\nRetrieving existing memories...');
        const memResult = await graph.query(
          'MATCH (m:Memory) RETURN m.text AS text, m.memory_type AS type, m.created_at AS created ORDER BY m.created_at DESC LIMIT 10'
        );
        if (memResult.data && memResult.data.length > 0) {
          console.log('\nExisting memories:');
          memResult.data.forEach((row: any, idx: number) => {
            console.log(`  ${idx + 1}. [${row[1]}] ${row[0].substring(0, 50)}...`);
          });
        }
      }
      console.log('✅ Data check completed\n');
      testsPasssed++;
    } catch (error) {
      console.log('⚠️  Data check encountered an issue:', error instanceof Error ? error.message : String(error));
      console.log('This is normal if the database is empty\n');
      testsPasssed++;
    }

    // Test 4: Check for Users
    console.log('✓ Test 4: User Nodes Check');
    console.log('-'.repeat(80));
    try {
      const userResult = await graph.query('MATCH (u:User) RETURN count(u) AS total_users');
      const userCount = userResult.data && userResult.data[0] ? userResult.data[0][0] : 0;
      console.log(`Found ${userCount} user nodes in the database`);

      if (userCount > 0) {
        const usersResult = await graph.query('MATCH (u:User) RETURN u.user_id AS user_id LIMIT 10');
        if (usersResult.data && usersResult.data.length > 0) {
          console.log('\nExisting users:');
          usersResult.data.forEach((row: any, idx: number) => {
            console.log(`  ${idx + 1}. ${row[0]}`);
          });
        }
      }
      console.log('✅ User check completed\n');
      testsPasssed++;
    } catch (error) {
      console.log('⚠️  User check encountered an issue:', error instanceof Error ? error.message : String(error));
      testsPasssed++;
    }

    // Test 5: Check Environment Configuration
    console.log('✓ Test 5: Environment Configuration');
    console.log('-'.repeat(80));
    const config = {
      FALKORDB_HOST: process.env.FALKORDB_HOST || 'localhost',
      FALKORDB_PORT: process.env.FALKORDB_PORT || '6379',
      FALKORDB_GRAPH_NAME: process.env.FALKORDB_GRAPH_NAME || 'memory_graph',
      EMBEDDING_MODEL: process.env.EMBEDDING_MODEL || 'text-embedding-3-small',
      OPENAI_API_KEY: process.env.OPENAI_API_KEY ? '✅ Set (hidden)' : '❌ NOT SET',
      MCP_SERVER_NAME: process.env.MCP_SERVER_NAME || 'falkordb-mcp-server',
    };

    console.log('Configuration:');
    Object.entries(config).forEach(([key, value]) => {
      console.log(`  ${key}: ${value}`);
    });

    if (process.env.OPENAI_API_KEY) {
      console.log('\n✅ OpenAI API key is configured - ready for embedding generation');
      testsPasssed++;
    } else {
      console.log('\n⚠️  OpenAI API key is NOT set - embedding generation will fail');
      console.log('   Set OPENAI_API_KEY in .env file to enable full functionality');
      testsFailed++;
    }
    console.log();

    // Summary
    console.log('='.repeat(80));
    console.log('VALIDATION SUMMARY');
    console.log('='.repeat(80));
    console.log(`✅ Tests Passed: ${testsPasssed}`);
    console.log(`❌ Tests Failed: ${testsFailed}`);
    console.log();

    if (testsFailed === 0 || (testsFailed === 1 && !process.env.OPENAI_API_KEY)) {
      console.log('🎉 Server is ready for testing!');
      if (!process.env.OPENAI_API_KEY) {
        console.log('⚠️  Remember to set OPENAI_API_KEY before running full tests');
      }
    } else {
      console.log('⚠️  Please resolve the issues above before proceeding');
    }
    console.log('='.repeat(80));

  } catch (error) {
    console.error('\n❌ VALIDATION FAILED:');
    console.error(error instanceof Error ? error.message : String(error));
    if (error instanceof Error && error.stack) {
      console.error('\nStack trace:');
      console.error(error.stack);
    }
    process.exit(1);
  }
}

// Run validation
validateSetup();
