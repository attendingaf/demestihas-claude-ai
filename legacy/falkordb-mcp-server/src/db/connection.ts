import { FalkorDB } from "falkordb";
import dotenv from "dotenv";

// Load environment variables
dotenv.config();

// Singleton database client instance
let dbClient: FalkorDB | null = null;

/**
 * Initialize the FalkorDB connection
 * This function should be called once at application startup
 */
export async function initializeDb(): Promise<void> {
    // Return early if already initialized
    if (dbClient !== null) {
        console.log("Database already initialized");
        return;
    }

    // Read connection details from environment variables
    const host = process.env.FALKORDB_HOST || "localhost";
    const port = parseInt(process.env.FALKORDB_PORT || "6379", 10);
    const username = process.env.FALKORDB_USERNAME || undefined;
    const password = process.env.FALKORDB_PASSWORD || undefined;
    const graphName = process.env.FALKORDB_GRAPH_NAME || "memory_graph";
    const maxConnections = parseInt(
        process.env.FALKORDB_MAX_CONNECTIONS || "10",
        10,
    );

    console.log(`Initializing FalkorDB connection to ${host}:${port}...`);

    try {
        // Create FalkorDB client instance with connection pooling
        const connectionOptions: any = {
            socket: {
                host,
                port,
            },
            poolOptions: {
                min: 1,
                max: maxConnections,
            },
        };

        // Only add username/password if they are defined
        if (username) connectionOptions.username = username;
        if (password) connectionOptions.password = password;

        const client = await FalkorDB.connect(connectionOptions);

        // Select the graph
        const graph = client.selectGraph(graphName);

        // Verify connection with test query
        const result = await graph.query("RETURN 1 AS test");

        // Check if the test query returned expected result
        if (result && result.data && result.data.length > 0) {
            // Connection successful, assign to singleton
            dbClient = client;
            console.log(`✓ Successfully connected to FalkorDB`);
            console.log(`✓ Using graph: ${graphName}`);
            console.log(`✓ Connection pool size: ${maxConnections}`);
        } else {
            throw new Error(
                "Connection test query did not return expected result",
            );
        }
    } catch (error) {
        // Log detailed error information
        console.error("Failed to connect to FalkorDB:");
        console.error(`  Host: ${host}`);
        console.error(`  Port: ${port}`);
        console.error(`  Graph: ${graphName}`);
        console.error(
            `  Error: ${error instanceof Error ? error.message : String(error)}`,
        );

        // Throw error to prevent server from starting in bad state
        throw new Error(
            `Database initialization failed: ${error instanceof Error ? error.message : String(error)}`,
        );
    }
}

/**
 * Get the initialized database client
 * @throws Error if database is not initialized
 * @returns The FalkorDB client instance
 */
export function getDb(): FalkorDB {
    if (dbClient === null) {
        throw new Error("Database not initialized. Call initializeDb() first.");
    }
    return dbClient;
}

/**
 * Close the database connection
 * Useful for graceful shutdown
 */
export async function closeDb(): Promise<void> {
    if (dbClient !== null) {
        await dbClient.close();
        dbClient = null;
        console.log("Database connection closed");
    }
}
