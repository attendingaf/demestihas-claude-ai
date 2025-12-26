#!/usr/bin/env node

/**
 * Direct MCP Server Test Script
 * Tests the FalkorDB MCP server tools directly via SSE
 */

import { Client } from "@modelcontextprotocol/sdk/client/index.js";
import { SSEClientTransport } from "@modelcontextprotocol/sdk/client/sse.js";

const SSE_URL = "https://claude.beltlineconsulting.co/sse";
const USER_ID = "mene";

async function testMcpServer() {
    try {
        console.log("=".repeat(80));
        console.log("FalkorDB MCP Server Direct Test");
        console.log("=".repeat(80));
        console.log();

        console.log(`Connecting to ${SSE_URL}...`);

        // Create SSE transport
        const transport = new SSEClientTransport(new URL(SSE_URL));

        // Create MCP client
        const client = new Client(
            {
                name: "test-client",
                version: "1.0.0",
            },
            {
                capabilities: {},
            }
        );

        // Connect to server
        await client.connect(transport);
        console.log("✅ Connected to MCP server\n");

        // List available tools
        console.log("📋 Available tools:");
        const tools = await client.listTools();
        tools.tools.forEach((tool) => {
            console.log(`  - ${tool.name}: ${tool.description}`);
        });
        console.log();

        // Test 1: Save private memory - Morning energy
        console.log("-".repeat(80));
        console.log("TEST 1: Save private memory - Morning energy");
        console.log("-".repeat(80));

        const memory1 = await client.callTool("save_memory", {
            user_id: USER_ID,
            text: "My morning energy peaks between 9-11am",
            memory_type: "private"
        });

        console.log("Response:", JSON.stringify(memory1, null, 2));
        console.log();

        // Wait a bit for the memory to be indexed
        await new Promise(resolve => setTimeout(resolve, 1000));

        // Test 2: Save private memory - Doctor info
        console.log("-".repeat(80));
        console.log("TEST 2: Save private memory - Doctor info");
        console.log("-".repeat(80));

        const memory2 = await client.callTool("save_memory", {
            user_id: USER_ID,
            text: "Dr. Sarah Chen is my primary care physician at Atlanta Medical",
            memory_type: "private"
        });

        console.log("Response:", JSON.stringify(memory2, null, 2));
        console.log();

        await new Promise(resolve => setTimeout(resolve, 1000));

        // Test 3: Save private memory - Work project
        console.log("-".repeat(80));
        console.log("TEST 3: Save private memory - Work project");
        console.log("-".repeat(80));

        const memory3 = await client.callTool("save_memory", {
            user_id: USER_ID,
            text: "Working on diabetes protocol revision for Q1 2025",
            memory_type: "private"
        });

        console.log("Response:", JSON.stringify(memory3, null, 2));
        console.log();

        await new Promise(resolve => setTimeout(resolve, 1000));

        // Test 4: Search for "doctor"
        console.log("-".repeat(80));
        console.log("TEST 4: Search for 'doctor'");
        console.log("-".repeat(80));

        const search1 = await client.callTool("search_memories", {
            user_id: USER_ID,
            query_text: "doctor",
            include_system: false,
            similarity_threshold: 0.7
        });

        console.log("Response:", JSON.stringify(search1, null, 2));
        console.log();

        // Test 5: Search for "morning energy"
        console.log("-".repeat(80));
        console.log("TEST 5: Search for 'morning energy'");
        console.log("-".repeat(80));

        const search2 = await client.callTool("search_memories", {
            user_id: USER_ID,
            query_text: "morning energy",
            include_system: false,
            similarity_threshold: 0.7
        });

        console.log("Response:", JSON.stringify(search2, null, 2));
        console.log();

        // Test 6: Get all recent memories
        console.log("-".repeat(80));
        console.log("TEST 6: Get all recent memories");
        console.log("-".repeat(80));

        const allMemories = await client.callTool("get_all_memories", {
            user_id: USER_ID,
            limit: 10
        });

        console.log("Response:", JSON.stringify(allMemories, null, 2));
        console.log();

        console.log("=".repeat(80));
        console.log("✅ All tests completed successfully!");
        console.log("=".repeat(80));

        // Close connection
        await client.close();
        process.exit(0);

    } catch (error) {
        console.error("\n❌ Test failed:");
        console.error(error instanceof Error ? error.message : String(error));
        if (error instanceof Error && error.stack) {
            console.error("\nStack trace:");
            console.error(error.stack);
        }
        process.exit(1);
    }
}

testMcpServer();
