#!/usr/bin/env node

/**
 * Complete test of memory operations via MCP SSE protocol
 */

const http = require('http');
const https = require('https');

async function testMemoryOperations(baseUrl, useHttps = false) {
    const protocol = useHttps ? https : http;
    const urlObj = new URL(baseUrl);

    console.log(`\n🧠 Testing Memory Operations with ${baseUrl}\n`);
    console.log('=' .repeat(80));

    return new Promise((resolve, reject) => {
        let sessionId = null;
        let messageId = 0;
        const responses = new Map();

        // Step 1: Open SSE connection
        const sseReq = protocol.get(`${baseUrl}/sse`, {
            headers: {
                'Accept': 'text/event-stream',
                'Connection': 'keep-alive'
            }
        }, (sseRes) => {
            console.log(`\n✓ SSE connection established (status: ${sseRes.statusCode})\n`);

            let buffer = '';

            sseRes.on('data', (chunk) => {
                buffer += chunk.toString();

                // Parse SSE messages
                const lines = buffer.split('\n');
                buffer = lines.pop(); // Keep incomplete line

                let currentEvent = null;
                let currentData = '';

                for (const line of lines) {
                    if (line.startsWith('event: ')) {
                        currentEvent = line.substring(7);
                    } else if (line.startsWith('data: ')) {
                        currentData += line.substring(6);
                    } else if (line === '' && currentEvent) {
                        // End of message
                        handleSSEMessage(currentEvent, currentData);
                        currentEvent = null;
                        currentData = '';
                    }
                }
            });

            function handleSSEMessage(event, data) {
                if (event === 'endpoint') {
                    console.log(`📍 Endpoint: ${data}`);
                    const match = data.match(/sessionId=([a-f0-9-]+)/);
                    if (match) {
                        sessionId = match[1];
                        console.log(`🔑 Session ID: ${sessionId}\n`);

                        // Start tests after getting session ID
                        runTests().catch(err => {
                            console.error('\n❌ Test suite failed:', err.message);
                            sseReq.destroy();
                            reject(err);
                        });
                    }
                } else if (event === 'message') {
                    try {
                        const msg = JSON.parse(data);
                        console.log(`📨 Received response: ${JSON.stringify(msg, null, 2)}\n`);

                        if (msg.id) {
                            responses.set(msg.id, msg);
                        }
                    } catch (e) {
                        console.error('Failed to parse message:', data);
                    }
                }
            }

            async function runTests() {
                console.log('=' .repeat(80));
                console.log('RUNNING MEMORY OPERATION TESTS');
                console.log('=' .repeat(80) + '\n');

                try {
                    // Test 1: List available tools
                    console.log('📋 Test 1: List available tools');
                    await sendRequest({
                        jsonrpc: "2.0",
                        id: ++messageId,
                        method: "tools/list"
                    });
                    await sleep(500);

                    // Test 2: Save a memory
                    console.log('💾 Test 2: Save a memory');
                    await sendRequest({
                        jsonrpc: "2.0",
                        id: ++messageId,
                        method: "tools/call",
                        params: {
                            name: "save_memory",
                            arguments: {
                                text: "My favorite programming language is TypeScript",
                                user_id: "mene",
                                memory_type: "private"
                            }
                        }
                    });
                    await sleep(1000);

                    // Test 3: Search memories
                    console.log('🔍 Test 3: Search memories');
                    await sendRequest({
                        jsonrpc: "2.0",
                        id: ++messageId,
                        method: "tools/call",
                        params: {
                            name: "search_memories",
                            arguments: {
                                query: "programming language",
                                user_id: "mene",
                                limit: 5
                            }
                        }
                    });
                    await sleep(1000);

                    // Test 4: Get all memories
                    console.log('📚 Test 4: Get all memories');
                    await sendRequest({
                        jsonrpc: "2.0",
                        id: ++messageId,
                        method: "tools/call",
                        params: {
                            name: "get_all_memories",
                            arguments: {
                                user_id: "mene",
                                limit: 10,
                                include_system: true
                            }
                        }
                    });
                    await sleep(1000);

                    console.log('\n' + '=' .repeat(80));
                    console.log('✅ ALL TESTS COMPLETED SUCCESSFULLY!');
                    console.log('=' .repeat(80) + '\n');

                    sseReq.destroy();
                    resolve();
                } catch (err) {
                    throw err;
                }
            }

            async function sendRequest(payload) {
                return new Promise((resolve, reject) => {
                    const postData = JSON.stringify(payload);

                    const options = {
                        hostname: urlObj.hostname,
                        port: urlObj.port || (useHttps ? 443 : 80),
                        path: `/message?sessionId=${sessionId}`,
                        method: 'POST',
                        headers: {
                            'Content-Type': 'application/json',
                            'Content-Length': Buffer.byteLength(postData),
                            'X-User-ID': 'mene'
                        }
                    };

                    console.log(`  → Sending: ${payload.method} (id: ${payload.id})`);

                    const req = protocol.request(options, (res) => {
                        let data = '';
                        res.on('data', (chunk) => { data += chunk.toString(); });
                        res.on('end', () => {
                            if (res.statusCode === 202 || res.statusCode === 200) {
                                console.log(`  ✓ Request accepted (${res.statusCode})`);
                                resolve();
                            } else {
                                reject(new Error(`HTTP ${res.statusCode}: ${data}`));
                            }
                        });
                    });

                    req.on('error', reject);
                    req.write(postData);
                    req.end();
                });
            }

            sseRes.on('error', (err) => {
                console.error('❌ SSE error:', err.message);
                reject(err);
            });
        });

        sseReq.on('error', (err) => {
            console.error('❌ SSE request error:', err.message);
            reject(err);
        });

        setTimeout(() => {
            console.error('❌ Timeout: Test took too long');
            sseReq.destroy();
            reject(new Error('Test timeout'));
        }, 30000);
    });
}

function sleep(ms) {
    return new Promise(resolve => setTimeout(resolve, ms));
}

// Main execution
const args = process.argv.slice(2);
const testUrl = args[0] || 'http://localhost:8050';
const useHttps = testUrl.startsWith('https://');

testMemoryOperations(testUrl, useHttps)
    .then(() => {
        console.log('✅ Test suite passed!\n');
        process.exit(0);
    })
    .catch((err) => {
        console.error('\n❌ Test suite failed:', err.message);
        process.exit(1);
    });
