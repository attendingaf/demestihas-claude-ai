import { getDb } from "../db/connection.js";
import { SAVE_PRIVATE_MEMORY, SAVE_SYSTEM_MEMORY } from "../db/queries.js";
import { getEmbedding } from "../embeddings/openai.js";
import { classifyMemory } from "../utils/memory-classifier.js";
import { saveMemorySchema, saveMemoryShape, type SaveMemoryInput } from "../utils/validators.js";

/**
 * Save Memory Tool
 *
 * Saves a piece of text as a memory for the user, either as a private or shared system memory.
 * Automatically generates a vector embedding for semantic search.
 *
 * Features:
 * - Automatic memory classification (private vs system)
 * - Vector embedding generation using OpenAI
 * - Graph storage with relationships in FalkorDB
 */
export const saveMemoryTool = {
    name: "save_memory",
    description:
        "Saves a piece of text as a memory for the user, either as a private or shared system memory. Generates a vector embedding for semantic search.",
    inputSchema: saveMemoryShape,

    /**
     * Handler function for the save_memory tool
     */
    handler: async (params: unknown) => {
        try {
            // Validate input parameters using Zod schema
            const validatedParams: SaveMemoryInput =
                saveMemorySchema.parse(params);

            console.log(`Saving memory for user: ${validatedParams.user_id}`);
            console.log(
                `Memory type requested: ${validatedParams.memory_type}`,
            );

            // Step 1: Generate embedding for the text
            console.log("Generating embedding...");
            const vector = await getEmbedding(validatedParams.text);
            console.log(
                `✓ Generated embedding with ${vector.length} dimensions`,
            );

            // Step 2: Classify memory type if set to 'auto'
            let finalMemoryType: "private" | "system";

            if (validatedParams.memory_type === "auto") {
                // Automatically classify the memory
                finalMemoryType = classifyMemory(validatedParams.text);
                console.log(`✓ Auto-classified memory as: ${finalMemoryType}`);
            } else {
                // Use the user-specified type
                finalMemoryType = validatedParams.memory_type as
                    | "private"
                    | "system";
                console.log(`✓ Using user-specified type: ${finalMemoryType}`);
            }

            // Step 3: Get database connection and select appropriate query
            const db = getDb();
            const graph = db.selectGraph(
                process.env.FALKORDB_GRAPH_NAME || "memory_graph",
            );

            const query =
                finalMemoryType === "private"
                    ? SAVE_PRIVATE_MEMORY
                    : SAVE_SYSTEM_MEMORY;

            // Step 4: Build query parameters
            const queryParams: Record<string, unknown> = {
                text: validatedParams.text,
                vector: vector,
            };

            // Add user_id only for private memories
            if (finalMemoryType === "private") {
                queryParams.user_id = validatedParams.user_id;
            }

            // Step 5: Execute the query
            console.log("Saving to database...");
            const result = await graph.query(query, { params: queryParams } as any);
            console.log("✓ Memory saved successfully");

            // Step 6: Return success response
            return {
                content: [
                    {
                        type: "text",
                        text: JSON.stringify(
                            {
                                success: true,
                                memory_type: finalMemoryType,
                                content: validatedParams.text,
                                user_id: validatedParams.user_id,
                                embedding_dimensions: vector.length,
                                saved_at: new Date().toISOString(),
                            },
                            null,
                            2,
                        ),
                    },
                ],
            };
        } catch (error) {
            // Log the error for debugging
            console.error("Error saving memory:");
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
                                error: "Failed to save memory",
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
