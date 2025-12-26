import { z } from "zod";

/**
 * Validation schema for the save_memory tool
 *
 * Validates that:
 * - user_id is a non-empty string
 * - text is a non-empty string
 * - memory_type is one of 'auto', 'private', or 'system' (defaults to 'auto')
 */
export const saveMemorySchema = z.object({
    user_id: z.string().min(1, "user_id must be a non-empty string"),
    text: z.string().min(1, "text must be a non-empty string"),
    memory_type: z.enum(["auto", "private", "system"]).default("auto"),
});

/**
 * Validation schema for the search_memories tool
 *
 * Validates that:
 * - user_id is a non-empty string
 * - query_text is a non-empty string
 * - include_system is a boolean (defaults to true)
 * - similarity_threshold is a number between 0 and 1 (defaults to 0.4)
 */
export const searchMemoriesSchema = z.object({
    user_id: z.string().min(1, "user_id must be a non-empty string"),
    query_text: z.string().min(1, "query_text must be a non-empty string"),
    include_system: z.boolean().default(true),
    similarity_threshold: z.number().min(0).max(1).default(0.4),
});

/**
 * Validation schema for the get_all_memories tool
 *
 * Validates that:
 * - user_id is a non-empty string
 * - include_system is a boolean (defaults to true)
 * - limit is a positive integer (defaults to 100)
 */
export const getAllMemoriesSchema = z.object({
    user_id: z.string().min(1, "user_id must be a non-empty string"),
    include_system: z.boolean().default(true),
    limit: z.number().int().positive().default(100),
});

// Export the shapes for MCP SDK (which expects ZodRawShape, not ZodObject)
export const saveMemoryShape = {
    user_id: z.string().min(1, "user_id must be a non-empty string"),
    text: z.string().min(1, "text must be a non-empty string"),
    memory_type: z.enum(["auto", "private", "system"]).default("auto"),
} as const;

export const searchMemoriesShape = {
    user_id: z.string().min(1, "user_id must be a non-empty string"),
    query_text: z.string().min(1, "query_text must be a non-empty string"),
    include_system: z.boolean().default(true),
    similarity_threshold: z.number().min(0).max(1).default(0.4),
} as const;

export const getAllMemoriesShape = {
    user_id: z.string().min(1, "user_id must be a non-empty string"),
    include_system: z.boolean().default(true),
    limit: z.number().int().positive().default(100),
} as const;

// Export TypeScript types inferred from the schemas
export type SaveMemoryInput = z.infer<typeof saveMemorySchema>;
export type SearchMemoriesInput = z.infer<typeof searchMemoriesSchema>;
export type GetAllMemoriesInput = z.infer<typeof getAllMemoriesSchema>;
