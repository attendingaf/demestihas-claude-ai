#!/usr/bin/env node

/**
 * Test HTTP Bridge and Rounds Mode functionality
 */

const EABootstrap = require('./bootstrap.js');

async function testHttpBridge() {
    console.log('Testing HTTP Bridge for Lyco 2.0...\n');

    try {
        // Initialize bootstrap
        console.log('1. Initializing EA-AI Bootstrap...');
        const initResult = await EABootstrap.init();
        console.log('   ✓ Bootstrap initialized in', initResult.bootstrapTime, 'ms');
        console.log('   ✓ Agents ready:', initResult.agents.join(', '));

        // Test operations that would use HTTP bridge
        const operations = [
            {
                name: 'Get Status',
                operation: 'get_status',
                params: {}
            },
            {
                name: 'Get Queue Preview',
                operation: 'get_queue_preview',
                params: {}
            },
            {
                name: 'Start Rounds',
                operation: 'start_rounds',
                params: {
                    rounds_type: 'morning'
                }
            }
        ];

        console.log('\n2. Testing Lyco HTTP Bridge operations:');

        for (const test of operations) {
            console.log(`\n   Testing: ${test.name}`);
            console.log(`   Operation: ${test.operation}`);

            try {
                const result = await EABootstrap.handleTaskOperation({
                    operation: test.operation,
                    ...test.params
                });

                if (result.status === 'error') {
                    console.log(`   ⚠ Error: ${result.error}`);
                    console.log('   Note: Make sure Lyco server is running on http://localhost:8000');
                } else {
                    console.log(`   ✓ Status: ${result.status}`);
                    if (result.data) {
                        console.log('   ✓ Response received:', JSON.stringify(result.data, null, 2).substring(0, 200) + '...');
                    }
                }
            } catch (error) {
                console.log(`   ✗ Failed: ${error.message}`);
            }
        }

        console.log('\n3. Testing MCP Server routing:');
        const routingTest = await EABootstrap.routeToAgent('lyco', {
            operation: 'get_status'
        });

        if (routingTest) {
            console.log('   ✓ Routing works:', routingTest.agent, '-', routingTest.status);
        } else {
            console.log('   ✗ Routing failed');
        }

        console.log('\n✅ HTTP Bridge test complete!');
        console.log('\nTo fully test the system:');
        console.log('1. Start Lyco server: cd agents/lyco/lyco-v2 && python server.py');
        console.log('2. Access Rounds UI: http://localhost:8000/rounds');
        console.log('3. From Claude Desktop: ea_ai_route lyco start_rounds');

    } catch (error) {
        console.error('Test failed:', error);
    }

    process.exit(0);
}

// Run test
testHttpBridge();
