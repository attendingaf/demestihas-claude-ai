import { getDb } from "../db/connection.js";
import { SEARCH_MEMORIES } from "../db/queries.js";
import { getEmbedding } from "../embeddings/openai.js";
import {
    searchMemoriesSchema,
    searchMemoriesShape,
    type SearchMemoriesInput,
} from "../utils/validators.js";

/**
 * Search Memories Tool
 *
 * Searches the user's private and system memories semantically using a query.
 * Returns a ranked list of the most similar memories based on vector similarity.
 *
 * Features:
 * - Semantic search using vector embeddings
 * - Filters by user (private memories) and optionally includes system memories
 * - Configurable similarity threshold
 * - Results ranked by similarity score
 */
export const searchMemoriesTool = {
    name: "search_memories",
    description:
        "Searches the user's private and system memories semantically using a query. Returns a ranked list of the most similar memories.",
    inputSchema: searchMemoriesShape,

    /**
     * Handler function for the search_memories tool
     */
    handler: async (params: unknown) => {
        try {
            // Validate input parameters using Zod schema
            const validatedParams: SearchMemoriesInput =
                searchMemoriesSchema.parse(params);

            console.log(
                `Searching memories for user: ${validatedParams.user_id}`,
            );
            console.log(`Query: "${validatedParams.query_text}"`);
            console.log(
                `Include system memories: ${validatedParams.include_system}`,
            );
            console.log(
                `Similarity threshold: ${validatedParams.similarity_threshold}`,
            );

            // Step 1: Generate embedding for the query text
            console.log("Generating query embedding...");
            const query_vector = await getEmbedding(validatedParams.query_text);
            console.log(
                `✓ Generated query embedding with ${query_vector.length} dimensions`,
            );

            // Step 2: Get database connection
            const db = getDb();
            const graph = db.selectGraph(
                process.env.FALKORDB_GRAPH_NAME || "memory_graph",
            );

            // Step 3: Build query with include_system filter
            // FalkorDB doesn't support boolean comparisons in WHERE clauses well,
            // so we handle include_system by modifying the query
            let searchQuery = SEARCH_MEMORIES;
            if (!validatedParams.include_system) {
                // If not including system memories, remove the system memory clause
                searchQuery = searchQuery.replace(
                    "WHERE\n    m.memory_type = 'system' OR",
                    "WHERE",
                );
            }

            const queryParams = {
                user_id: validatedParams.user_id,
                query_vector: query_vector,
                similarity_threshold: validatedParams.similarity_threshold,
            };

            // Step 4: Execute search query
            console.log("Executing semantic search...");
            const result = await graph.query(searchQuery, {
                params: queryParams,
            });

            // Step 5: Format and return results
            const memories = result.data || [];
            console.log(`✓ Found ${memories.length} matching memories`);

            // Format the results for better readability
            const formattedResults = memories.map((row: any) => ({
                text: row[0], // text
                memory_type: row[1], // memory_type
                created_at: row[2], // created_at
                subject: row[3], // subject
                predicate: row[4], // predicate
                object: row[5], // object
                similarity: row[6], // similarity score
            }));

            return {
                content: [
                    {
                        type: "text",
                        text: JSON.stringify(
                            {
                                success: true,
                                query: validatedParams.query_text,
                                user_id: validatedParams.user_id,
                                count: formattedResults.length,
                                threshold: validatedParams.similarity_threshold,
                                results: formattedResults,
                            },
                            null,
                            2,
                        ),
                    },
                ],
            };
        } catch (error) {
            // Log the error for debugging
            console.error("Error searching memories:");
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
                                error: "Failed to search memories",
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
