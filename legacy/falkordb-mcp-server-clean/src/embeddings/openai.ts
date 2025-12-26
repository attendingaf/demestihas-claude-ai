import OpenAI from "openai";
import dotenv from "dotenv";

// Load environment variables
dotenv.config();

// Validate API key
const apiKey = process.env.OPENAI_API_KEY;
if (!apiKey) {
    throw new Error("OPENAI_API_KEY environment variable is required");
}

// Initialize OpenAI client
const openai = new OpenAI({
    apiKey: apiKey,
});

/**
 * Generate an embedding vector for the given text using OpenAI's API
 *
 * @param text - The text to generate an embedding for
 * @returns The embedding vector as an array of numbers
 * @throws Error if the API call fails
 */
export async function getEmbedding(text: string): Promise<number[]> {
    // Read embedding model from environment
    const modelName = process.env.EMBEDDING_MODEL || "text-embedding-3-small";

    try {
        // Call OpenAI embeddings API
        const response = await openai.embeddings.create({
            input: text,
            model: modelName,
        });

        // Extract and return the embedding vector
        const embedding = response.data[0]?.embedding;

        if (!embedding) {
            throw new Error("No embedding returned from OpenAI API");
        }

        return embedding;
    } catch (error) {
        // Log detailed error information
        console.error("OpenAI embedding API error:");
        console.error(`  Model: ${modelName}`);
        console.error(`  Text length: ${text.length} characters`);
        console.error(
            `  Error: ${error instanceof Error ? error.message : String(error)}`,
        );

        // Re-throw the error so calling functions can handle it
        throw error;
    }
}
