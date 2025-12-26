import dotenv from "dotenv";

// Load environment variables at the very top
dotenv.config();

import { McpServer } from "@modelcontextprotocol/sdk/server/mcp.js";
import { StdioServerTransport } from "@modelcontextprotocol/sdk/server/stdio.js";
import { initializeDb } from "./db/connection.js";
import { saveMemoryTool } from "./tools/save-memory.js";
import { searchMemoriesTool } from "./tools/search-memories.js";
import { getAllMemoriesTool } from "./tools/get-all-memories.js";

/**
 * Main server startup function
 */
async function startServer(): Promise<void> {
    try {
        console.log("Starting FalkorDB MCP Server...");

        // Step 1: Initialize database connection
        await initializeDb();
        console.log("✓ FalkorDB connection established");

        // Step 2: Read server configuration from environment
        const serverName = process.env.MCP_SERVER_NAME || "falkordb-mcp-server";
        const serverVersion = process.env.MCP_SERVER_VERSION || "1.0.0";

        console.log(`Server name: ${serverName}`);
        console.log(`Server version: ${serverVersion}`);

        // Step 3: Initialize MCP Server
        const server = new McpServer(
            {
                name: serverName,
                version: serverVersion,
            },
            {
                capabilities: {
                    tools: {},
                },
            },
        );

        console.log("✓ MCP Server instance created");

        // Register tools
        server.registerTool(
            saveMemoryTool.name,
            {
                description: saveMemoryTool.description,
                inputSchema: saveMemoryTool.inputSchema,
            },
            saveMemoryTool.handler as any,
        );

        console.log("✓ Registered tool: save_memory");

        server.registerTool(
            searchMemoriesTool.name,
            {
                description: searchMemoriesTool.description,
                inputSchema: searchMemoriesTool.inputSchema,
            },
            searchMemoriesTool.handler as any,
        );

        console.log("✓ Registered tool: search_memories");

        server.registerTool(
            getAllMemoriesTool.name,
            {
                description: getAllMemoriesTool.description,
                inputSchema: getAllMemoriesTool.inputSchema,
            },
            getAllMemoriesTool.handler as any,
        );

        console.log("✓ Registered tool: get_all_memories");
        console.log(`✓ All ${3} tools registered successfully`);

        // Step 4: Start server with stdio transport
        // MCP servers typically use stdio for communication with clients
        const transport = new StdioServerTransport();
        await server.connect(transport);

        console.log(
            `✓ Server '${serverName}' is now running and listening for MCP requests`,
        );
        console.log("✓ Ready to accept tool calls");
    } catch (error) {
        // Log detailed error information
        console.error("Failed to start server:");
        console.error(error instanceof Error ? error.message : String(error));

        if (error instanceof Error && error.stack) {
            console.error("Stack trace:");
            console.error(error.stack);
        }

        // Exit with error code to prevent running in a bad state
        process.exit(1);
    }
}

// Execute the server startup
startServer();
