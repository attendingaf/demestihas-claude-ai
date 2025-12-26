import { getDb } from "../db/connection.js";
import { GET_ALL_MEMORIES } from "../db/queries.js";
import {
    getAllMemoriesSchema,
    getAllMemoriesShape,
    type GetAllMemoriesInput,
} from "../utils/validators.js";

/**
 * Get All Memories Tool
 *
 * Retrieves all memories for a user, sorted by most recent.
 * Can optionally include shared system memories.
 *
 * Features:
 * - Retrieves all user memories (private and optionally system)
 * - Sorted by creation date (newest first)
 * - Configurable result limit
 * - No embedding or similarity calculation needed
 */
export const getAllMemoriesTool = {
    name: "get_all_memories",
    description:
        "Retrieves all memories for a user, sorted by most recent. Can optionally include shared system memories.",
    inputSchema: getAllMemoriesShape,

    /**
     * Handler function for the get_all_memories tool
     */
    handler: async (params: unknown) => {
        try {
            // Validate input parameters using Zod schema
            const validatedParams: GetAllMemoriesInput =
                getAllMemoriesSchema.parse(params);

            console.log(
                `Retrieving all memories for user: ${validatedParams.user_id}`,
            );
            console.log(
                `Include system memories: ${validatedParams.include_system}`,
            );
            console.log(`Limit: ${validatedParams.limit}`);

            // Step 1: Get database connection
            const db = getDb();
            const graph = db.selectGraph(
                process.env.FALKORDB_GRAPH_NAME || "memory_graph",
            );

            // Step 2: Validate and sanitize limit for security
            // LIMIT must be a positive integer - Zod already validates this,
            // but we add bounds checking for additional safety
            const safeLimit = Math.max(
                1,
                Math.min(10000, validatedParams.limit),
            );

            // Step 3: Build query with interpolated LIMIT and include_system filter
            // FalkorDB doesn't support parameterized LIMIT or boolean comparisons well,
            // so we interpolate these values directly into the query string
            let queryWithLimit = GET_ALL_MEMORIES.replace(
                "LIMIT $limit",
                `LIMIT ${safeLimit}`,
            );

            // Handle include_system parameter by modifying WHERE clause
            if (!validatedParams.include_system) {
                // If not including system memories, add filter to exclude them
                queryWithLimit = queryWithLimit.replace(
                    "WHERE\n    m.memory_type = 'system' OR",
                    "WHERE",
                );
            }

            const queryParams = {
                user_id: validatedParams.user_id,
            };

            // Step 4: Execute query
            console.log("Executing query...");
            const result = await graph.query(queryWithLimit, {
                params: queryParams,
            });

            // Step 5: Format and return results
            const memories = result.data || [];
            console.log(`✓ Retrieved ${memories.length} memories`);

            // Format the results for better readability
            const formattedResults = memories.map((row: any) => ({
                text: row[0], // text
                memory_type: row[1], // memory_type
                created_at: row[2], // created_at
                subject: row[3], // subject
                predicate: row[4], // predicate
                object: row[5], // object
            }));

            return {
                content: [
                    {
                        type: "text",
                        text: JSON.stringify(
                            {
                                success: true,
                                user_id: validatedParams.user_id,
                                count: formattedResults.length,
                                limit: validatedParams.limit,
                                include_system: validatedParams.include_system,
                                memories: formattedResults,
                            },
                            null,
                            2,
                        ),
                    },
                ],
            };
        } catch (error) {
            // Log the error for debugging
            console.error("Error retrieving memories:");
            console.error(
                error instanceof Error ? error.message : String(error),
            );

            if (error instanceof Error && error.stack) {
                console.error("Stack trace:", error.stack);
            }

            // Return error response
            return {
                content: [
                    {
                        type: "text",
                        text: JSON.stringify(
                            {
                                success: false,
                                error: "Failed to retrieve memories",
                                details:
                                    error instanceof Error
                                        ? error.message
                                        : String(error),
                            },
                            null,
                            2,
                        ),
                    },
                ],
                isError: true,
            };
        }
    },
};
