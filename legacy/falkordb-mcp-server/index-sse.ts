import dotenv from "dotenv";

// Load environment variables at the very top
dotenv.config();

import { McpServer } from "@modelcontextprotocol/sdk/server/mcp.js";
import { SSEServerTransport } from "@modelcontextprotocol/sdk/server/sse.js";
import { initializeDb, getDb } from "./db/connection.js";
import { saveMemoryTool } from "./tools/save-memory.js";
import { searchMemoriesTool } from "./tools/search-memories.js";
import { getAllMemoriesTool } from "./tools/get-all-memories.js";
import express from "express";
import cors from "cors";

/**
 * Main server startup function for SSE transport
 */
async function startServer(): Promise<void> {
    try {
        console.log("Starting FalkorDB MCP Server with SSE transport...");

        // Step 1: Initialize database connection
        await initializeDb();
        console.log("✓ FalkorDB connection established");

        // Step 2: Read server configuration from environment
        const serverName = process.env.MCP_SERVER_NAME || "falkordb-mcp-server";
        const serverVersion = process.env.MCP_SERVER_VERSION || "1.0.0";
        const port = parseInt(process.env.SSE_PORT || "8050", 10);
        const host = process.env.SSE_HOST || "0.0.0.0";

        console.log(`Server name: ${serverName}`);
        console.log(`Server version: ${serverVersion}`);
        console.log(`SSE Port: ${port}`);
        console.log(`SSE Host: ${host}`);

        // Step 4: Create Express app for SSE transport
        const app = express();

        // Enable CORS for remote access
        app.use(
            cors({
                origin: "*",
                methods: ["GET", "POST", "OPTIONS"],
                allowedHeaders: ["Content-Type", "Authorization"],
                credentials: true,
            }),
        );

        app.use(express.json());

        // Store active transports by session ID
        const transports = new Map();

        // Health check endpoint
        app.get("/health", (req, res) => {
            res.json({
                status: "ok",
                server: serverName,
                version: serverVersion,
            });
        });

        // SSE endpoint - creates a new server instance per connection
        app.get("/sse", async (req, res) => {
            console.log("New SSE connection established from:", req.ip);

            // Create a new MCP server instance for this connection
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

            // Register tools for this server instance
            server.registerTool(
                saveMemoryTool.name,
                {
                    description: saveMemoryTool.description,
                    inputSchema: saveMemoryTool.inputSchema,
                },
                saveMemoryTool.handler,
            );

            server.registerTool(
                searchMemoriesTool.name,
                {
                    description: searchMemoriesTool.description,
                    inputSchema: searchMemoriesTool.inputSchema,
                },
                searchMemoriesTool.handler,
            );

            server.registerTool(
                getAllMemoriesTool.name,
                {
                    description: getAllMemoriesTool.description,
                    inputSchema: getAllMemoriesTool.inputSchema,
                },
                getAllMemoriesTool.handler,
            );

            console.log("✓ Tools registered for new connection");

            // Create SSE transport
            const transport = new SSEServerTransport("/message", res);

            // Store the transport so we can access it from the message endpoint
            const sessionId = transport.sessionId;
            transports.set(sessionId, transport);

            // Clean up when connection closes
            res.on("close", () => {
                console.log(`SSE connection closed for session: ${sessionId}`);
                transports.delete(sessionId);
            });

            // Connect the server to this transport
            await server.connect(transport);

            console.log(
                `✓ Server connected to SSE transport (session: ${sessionId})`,
            );
        });

        // Message endpoint for client requests
        app.post("/message", async (req, res) => {
            const sessionId = req.query.sessionId;

            if (!sessionId || typeof sessionId !== "string") {
                console.error(
                    "Missing or invalid sessionId in message request",
                );
                return res.status(400).json({ error: "Missing sessionId" });
            }

            const transport = transports.get(sessionId);

            if (!transport) {
                console.error(`No transport found for session: ${sessionId}`);
                return res.status(404).json({ error: "Session not found" });
            }

            console.log(`Received message for session: ${sessionId}`);

            try {
                // The transport will handle the message
                // Pass req.body as third parameter since express.json() already parsed it
                await transport.handlePostMessage(req, res, req.body);
            } catch (error) {
                console.error("Error handling message:", error);
                // Only send error response if headers not already sent
                if (!res.headersSent) {
                    res.status(500).json({ error: "Internal server error" });
                }
            }
        });

        // Auth Middleware
        const authMiddleware = (req: express.Request, res: express.Response, next: express.NextFunction) => {
            const authHeader = req.headers.authorization;
            const apiKey = process.env.FALKOR_API_KEY;

            if (!apiKey) {
                console.error("FALKOR_API_KEY not set in environment");
                return res.status(500).json({ error: "Server configuration error" });
            }

            if (!authHeader || !authHeader.startsWith("Bearer ") || authHeader.split(" ")[1] !== apiKey) {
                return res.status(401).json({ error: "Unauthorized" });
            }
            next();
        };

        const graphName = process.env.FALKORDB_GRAPH_NAME || "memory_graph";

        // 1. Execute Cypher Query
        app.post("/graph/query", authMiddleware, async (req, res) => {
            try {
                const { cypher, params } = req.body;
                if (!cypher) return res.status(400).json({ error: "Missing cypher query" });

                const client = getDb();
                const graph = client.selectGraph(graphName);
                const startTime = Date.now();
                const result: any = await graph.query(cypher, { params } as any);
                const executionTime = Date.now() - startTime;

                // Extract statistics if available, otherwise default to 0
                // Note: The actual property names depend on the FalkorDB client version
                const nodesCreated = (result as any).nodesCreated || 0;
                const relationshipsCreated = (result as any).relationshipsCreated || 0;

                res.json({
                    success: true,
                    results: result.data,
                    metadata: {
                        nodes_created: nodesCreated,
                        relationships_created: relationshipsCreated,
                        execution_time_ms: executionTime
                    }
                });
            } catch (error) {
                res.status(500).json({
                    success: false,
                    error: error instanceof Error ? error.message : String(error),
                    code: "CYPHER_ERROR"
                });
            }
        });

        // 2. Create Nodes
        app.post("/graph/nodes", authMiddleware, async (req, res) => {
            try {
                const { label, properties } = req.body;
                if (!label) return res.status(400).json({ error: "Missing label" });

                const client = getDb();
                const graph = client.selectGraph(graphName);

                // Construct CREATE query
                const props = properties || {};
                const query = `CREATE (n:${label} $props) RETURN n`;
                const result: any = await graph.query(query, { params: { props } } as any);

                if (!result.data || result.data.length === 0) {
                    return res.status(500).json({ success: false, error: "Failed to create node" });
                }

                const node: any = result.data[0]['n'];

                res.json({
                    success: true,
                    node_id: node.id,
                    label: label,
                    properties: node.properties
                });
            } catch (error) {
                res.status(500).json({ success: false, error: String(error) });
            }
        });

        // 3. Create Relationships
        app.post("/graph/relationships", authMiddleware, async (req, res) => {
            try {
                const { from_label, from_match, to_label, to_match, relationship_type, properties } = req.body;

                if (!from_label || !to_label || !relationship_type) {
                    return res.status(400).json({ error: "Missing required fields" });
                }

                const client = getDb();
                const graph = client.selectGraph(graphName);

                const query = `
            MATCH (a:${from_label}), (b:${to_label})
            WHERE ${Object.keys(from_match).map(k => `a.${k} = $from_${k}`).join(' AND ')}
            AND ${Object.keys(to_match).map(k => `b.${k} = $to_${k}`).join(' AND ')}
            CREATE (a)-[r:${relationship_type} $props]->(b)
            RETURN a, r, b
        `;

                const params: any = { props: properties || {} };
                Object.entries(from_match).forEach(([k, v]) => params[`from_${k}`] = v);
                Object.entries(to_match).forEach(([k, v]) => params[`to_${k}`] = v);

                const result: any = await graph.query(query, { params } as any);

                if (result.data.length === 0) {
                    return res.status(404).json({ success: false, error: "Source or target node not found" });
                }

                const row: any = result.data[0];
                res.json({
                    success: true,
                    relationship_type,
                    from_node: row['a'],
                    to_node: row['b']
                });

            } catch (error) {
                res.status(500).json({ success: false, error: String(error) });
            }
        });

        // 4. Search Nodes
        app.get("/graph/search", authMiddleware, async (req, res) => {
            try {
                const { label, property, value } = req.query;

                if (!label || !property || !value) {
                    return res.status(400).json({ error: "Missing required query parameters" });
                }

                const client = getDb();
                const graph = client.selectGraph(graphName);

                const query = `MATCH (n:${label}) WHERE n.${String(property)} = $value RETURN n`;
                const result: any = await graph.query(query, { params: { value } } as any);

                res.json({
                    success: true,
                    count: result.data.length,
                    results: result.data ? result.data.map((row: any) => row['n']) : []
                });
            } catch (error) {
                res.status(500).json({ success: false, error: String(error) });
            }
        });

        // 5. Get Node with Relationships
        app.get("/graph/node/:label/:property/:value/relationships", authMiddleware, async (req, res) => {
            try {
                const { label, property, value } = req.params;
                const client = getDb();
                const graph = client.selectGraph(graphName);

                // Get node and outgoing relationships
                const outQuery = `
            MATCH (n:${label})-[r]->(m)
            WHERE n.${property} = $value
            RETURN type(r) as type, m as target
        `;

                // Get node and incoming relationships
                const inQuery = `
            MATCH (n:${label})<-[r]-(m)
            WHERE n.${property} = $value
            RETURN type(r) as type, m as source
        `;

                // Get the node itself
                const nodeQuery = `MATCH (n:${label}) WHERE n.${property} = $value RETURN n`;

                const [outResult, inResult, nodeResult] = await Promise.all([
                    graph.query(outQuery, { params: { value } } as any) as Promise<any>,
                    graph.query(inQuery, { params: { value } } as any) as Promise<any>,
                    graph.query(nodeQuery, { params: { value } } as any) as Promise<any>
                ]);

                if (!nodeResult.data || nodeResult.data.length === 0) {
                    return res.status(404).json({ success: false, error: "Node not found" });
                }

                res.json({
                    success: true,
                    node: nodeResult.data[0]['n'],
                    relationships: {
                        outgoing: outResult.data || [],
                        incoming: inResult.data || []
                    }
                });

            } catch (error) {
                res.status(500).json({ success: false, error: String(error) });
            }
        });

        // 6. Bulk Import
        app.post("/graph/bulk", authMiddleware, async (req, res) => {
            try {
                const { nodes, relationships } = req.body;
                const client = getDb();
                const graph = client.selectGraph(graphName);

                let nodesCreated = 0;
                let relationshipsCreated = 0;
                const errors: any[] = [];

                // Create nodes
                if (nodes && Array.isArray(nodes)) {
                    for (const node of nodes) {
                        try {
                            const query = `CREATE (n:${node.label} $props)`;
                            await graph.query(query, { params: { props: node.properties } } as any);
                            nodesCreated++;
                        } catch (e) {
                            errors.push({ item: node, error: String(e) });
                        }
                    }
                }

                // Create relationships
                if (relationships && Array.isArray(relationships)) {
                    for (const rel of relationships) {
                        try {
                            const query = `
                        MATCH (a:${rel.from.label}), (b:${rel.to.label})
                        WHERE ${Object.keys(rel.from.match).map(k => `a.${k} = $from_${k}`).join(' AND ')}
                        AND ${Object.keys(rel.to.match).map(k => `b.${k} = $to_${k}`).join(' AND ')}
                        CREATE (a)-[r:${rel.type} $props]->(b)
                    `;

                            const params: any = { props: rel.properties || {} };
                            Object.entries(rel.from.match).forEach(([k, v]) => params[`from_${k}`] = v);
                            Object.entries(rel.to.match).forEach(([k, v]) => params[`to_${k}`] = v);

                            await graph.query(query, { params } as any);
                            relationshipsCreated++;
                        } catch (e) {
                            errors.push({ item: rel, error: String(e) });
                        }
                    }
                }

                res.json({
                    success: true,
                    nodes_created: nodesCreated,
                    relationships_created: relationshipsCreated,
                    errors
                });

            } catch (error) {
                res.status(500).json({ success: false, error: String(error) });
            }
        });

        // Start listening
        app.listen(port, host, () => {
            console.log(
                `✓ Server '${serverName}' is now running on http://${host}:${port}`,
            );
            console.log(`✓ SSE endpoint: http://${host}:${port}/sse`);
            console.log(`✓ Health check: http://${host}:${port}/health`);
            console.log("✓ Ready to accept tool calls");
        });
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
