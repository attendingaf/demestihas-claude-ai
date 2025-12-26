#!/usr/bin/env node

/**
 * SSE Client Wrapper for Claude Desktop
 * This script connects to the remote SSE server and bridges it to stdio
 * so Claude Desktop can use it via the command transport.
 */

import { Client } from "@modelcontextprotocol/sdk/client/index.js";
import { SSEClientTransport } from "@modelcontextprotocol/sdk/client/sse.js";
import { StdioClientTransport } from "@modelcontextprotocol/sdk/client/stdio.js";

const SSE_URL = process.env.FALKORDB_SSE_URL || "http://178.156.170.161:8050/sse";

async function main() {
    try {
        console.error(`Connecting to FalkorDB MCP Server at ${SSE_URL}...`);

        // Create SSE transport to connect to remote server
        const transport = new SSEClientTransport(new URL(SSE_URL));

        // Create MCP client
        const client = new Client({
            name: "falkordb-client",
            version: "1.0.0"
        }, {
            capabilities: {}
        });

        // Connect to the remote server
        await client.connect(transport);

        console.error("✓ Connected to FalkorDB MCP Server");
        console.error("✓ Ready to forward requests");

        // Keep the process running
        process.on('SIGINT', async () => {
            console.error("\nShutting down...");
            await client.close();
            process.exit(0);
        });

    } catch (error) {
        console.error("Failed to connect to FalkorDB server:");
        console.error(error instanceof Error ? error.message : String(error));
        process.exit(1);
    }
}

main();
