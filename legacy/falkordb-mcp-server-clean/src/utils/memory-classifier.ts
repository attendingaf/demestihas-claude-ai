/**
 * Memory types that can be assigned to memories
 * - private: Personal, sensitive information belonging to a specific user
 * - system: General knowledge, facts, or non-personal information
 */
export type MemoryType = "private" | "system";

/**
 * Private indicators - keywords and patterns that suggest private information
 * These patterns indicate personal, sensitive, or user-specific information
 */
const PRIVATE_INDICATORS = [
    // Personal identifiers
    "my password",
    "my pin",
    "my ssn",
    "social security",

    // Financial information
    "my bank",
    "my credit card",
    "my account",
    "my balance",

    // Health information
    "my health",
    "my medical",
    "my diagnosis",
    "my doctor",
    "my prescription",

    // Personal feelings and thoughts
    "i feel",
    "i think",
    "i believe",
    "i want",
    "i need",
    "i wish",
    "i hope",
    "i am",
    "i'm",

    // Personal relationships
    "my family",
    "my friend",
    "my partner",
    "my spouse",
    "my relationship",

    // Personal possessions and locations
    "my home",
    "my address",
    "my phone",
    "my email",
    "my car",

    // Personal plans and activities
    "my schedule",
    "my appointment",
    "my meeting",
    "my vacation",
    "my trip",

    // Identity and preferences
    "my name",
    "my preference",
    "my favorite",
    "my birthday",
    "my age",
];

/**
 * Classifies memory text as either 'private' or 'system'
 *
 * Classification logic:
 * 1. Checks for private indicators (personal keywords)
 * 2. Defaults to 'private' for safety if uncertain
 *
 * Note: This is a simple keyword-based classifier. In production,
 * you might want to use more sophisticated NLP or ML-based classification.
 *
 * @param text - The memory text to classify
 * @returns 'private' or 'system'
 */
export function classifyMemory(text: string): MemoryType {
    // Convert text to lowercase for case-insensitive matching
    const lowerText = text.toLowerCase();

    // Check if any private indicator is present in the text
    const hasPrivateIndicator = PRIVATE_INDICATORS.some((indicator) =>
        lowerText.includes(indicator),
    );

    if (hasPrivateIndicator) {
        return "private";
    }

    // Default to 'private' for safety
    // Per the plan: "If uncertain, default to private for safety"
    // This ensures we err on the side of caution with potentially sensitive information
    return "private";
}
