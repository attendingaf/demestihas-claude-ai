const { spawn } = require('child_process');

console.log('Testing EA-AI MCP Server JSON-RPC compliance...\n');

const server = spawn('node', ['../mcp-server-fixed.js']);

let output = '';
let errorOutput = '';

server.stdout.on('data', (data) => {
  output += data.toString();
});

server.stderr.on('data', (data) => {
  errorOutput += data.toString();
});

// Test initialize request
const testRequest = {
  method: "initialize",
  params: {
    protocolVersion: "2025-06-18",
    capabilities: {},
    clientInfo: {
      name: "test",
      version: "1.0.0"
    }
  },
  jsonrpc: "2.0",
  id: 1
};

server.stdin.write(JSON.stringify(testRequest) + '\n');

setTimeout(() => {
  console.log('Server stderr output:');
  console.log(errorOutput);
  console.log('\nServer response:');
  
  try {
    const response = JSON.parse(output);
    console.log(JSON.stringify(response, null, 2));
    
    // Validate response
    if (response.jsonrpc === "2.0" && response.id === 1 && response.result) {
      console.log('\n✅ Test PASSED: Server returned valid JSON-RPC 2.0 response');
    } else {
      console.log('\n❌ Test FAILED: Invalid response format');
    }
  } catch (e) {
    console.log('Raw output:', output);
    console.log('\n❌ Test FAILED: Could not parse response as JSON');
  }
  
  server.kill();
  process.exit(0);
}, 1000);
