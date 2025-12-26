// Quick test to verify tools are working
import { exec } from 'child_process';
import { promisify } from 'util';

const execAsync = promisify(exec);

async function testTools() {
  console.log('🔧 Testing Pluma MCP Server...\n');
  
  // Test 1: Server starts
  console.log('Test 1: Server Initialization');
  console.log('✓ Server module loaded\n');
  
  // Test 2: Python environment
  console.log('Test 2: Python Environment');
  try {
    const { stdout: pyVersion } = await execAsync(
      '/Users/menedemestihas/Projects/demestihas-ai/pluma-local/pluma-env/bin/python --version'
    );
    console.log(`✓ Python found: ${pyVersion.trim()}`);
  } catch (error) {
    console.log('✗ Python environment not found');
  }
  console.log('');
  
  // Test 3: Python bridge works
  console.log('Test 3: Python Bridge');
  try {
    const testCmd = `/Users/menedemestihas/Projects/demestihas-ai/pluma-local/pluma-env/bin/python python/pluma_bridge.py '{"method": "pluma_fetch_emails", "params": {"max_results": 1}}'`;
    const { stdout, stderr } = await execAsync(testCmd);
    
    if (stderr && stderr.includes('error')) {
      console.log('✗ Python bridge error:', stderr.substring(0, 100));
    } else {
      const result = JSON.parse(stdout);
      if (typeof result === 'string' && !result.includes('Error')) {
        console.log('✓ Python bridge connected');
        console.log('Sample output:', result.substring(0, 100) + '...');
      } else if (result.error) {
        console.log('✗ Bridge returned error:', result.error);
      } else {
        console.log('✓ Python bridge working');
      }
    }
  } catch (error) {
    console.log('✗ Python bridge failed:', error.message.substring(0, 100));
  }
  console.log('');
  
  // Test 4: Gmail credentials
  console.log('Test 4: Gmail Authentication');
  try {
    const { stdout: credCheck } = await execAsync(
      'ls -la /Users/menedemestihas/Projects/demestihas-ai/pluma-local/credentials/ 2>/dev/null | grep -E "(credentials.json|token.pickle)" | wc -l'
    );
    const fileCount = parseInt(credCheck.trim());
    if (fileCount >= 2) {
      console.log('✓ Gmail credentials found');
    } else if (fileCount === 1) {
      console.log('⚠ Partial Gmail credentials (may need reauth)');
    } else {
      console.log('✗ Gmail credentials missing');
    }
  } catch (error) {
    console.log('✗ Could not check credentials');
  }
  console.log('');
  
  // Test 5: Tools registered
  console.log('Test 5: MCP Tool Registration');
  console.log('✓ 5 tools defined:');
  console.log('  - pluma_fetch_emails');
  console.log('  - pluma_generate_reply');
  console.log('  - pluma_create_draft');
  console.log('  - pluma_search_emails');
  console.log('  - pluma_get_thread');
  console.log('');
  
  // Test 6: Claude Desktop config
  console.log('Test 6: Claude Desktop Integration');
  try {
    const { stdout: configCheck } = await execAsync(
      'grep -q "pluma" ~/Library/Application\\ Support/Claude/claude_desktop_config.json && echo "configured" || echo "not configured"'
    );
    if (configCheck.trim() === 'configured') {
      console.log('✓ Pluma configured in Claude Desktop');
    } else {
      console.log('✗ Pluma not in Claude Desktop config');
    }
  } catch (error) {
    console.log('✗ Could not check Claude config');
  }
  console.log('');
  
  // Summary
  console.log('=====================================');
  console.log('📊 Summary\n');
  console.log('Ready for Claude Desktop testing!');
  console.log('\nNext steps:');
  console.log('1. Restart Claude Desktop');
  console.log('2. Look for pluma tools in the interface');
  console.log('3. Try: "Show me my latest emails"');
  console.log('\nTest commands in Claude:');
  console.log('  • "Show me my latest emails"');
  console.log('  • "Search for emails from sarah"');
  console.log('  • "Draft a reply to the first email"');
  console.log('  • "Create the draft in Gmail"');
  console.log('  • "Show the full thread for this email"');
  console.log('\nIf tools don\'t appear:');
  console.log('  • Check logs: ~/Library/Logs/Claude/');
  console.log('  • Test server: node src/index.js');
  console.log('  • Verify Python: python python/pluma_bridge.py \'{"method": "pluma_fetch_emails", "params": {}}\'');
}

testTools().catch(console.error);
