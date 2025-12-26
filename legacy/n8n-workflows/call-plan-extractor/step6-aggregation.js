// Initialize result structure
const result = {
    mene_actions: [],
    followup_items: [],
    documents_processed: [],
    run_timestamp: new Date().toISOString()
};

// Loop over all input items (from the AI Agent node)
// Note: Depending on how the Loop is configured, you might need to ensure this node runs "Once for all items" 
// or accumulates the output. If using the "Loop Over Items" node, this Code node should probably be placed 
// after the Loop node finishes, receiving the aggregated output of the loop.

for (const item of $input.all()) {
    try {
        // Attempt to locate the AI output. 
        // Common keys: 'output', 'text', 'response', or 'message.content'.
        // Adjust 'output' to the actual key returned by your AI Agent node.
        let contentRaw = item.json.output || item.json.text || item.json.response || (item.json.message && item.json.message.content);

        if (!contentRaw) continue;

        // If the AI returned code blocks (```json ... ```), strip them
        if (typeof contentRaw === 'string') {
            contentRaw = contentRaw.replace(/```json/g, '').replace(/```/g, '').trim();
        }

        // Parse JSON if it is a string
        let parsedOutput = (typeof contentRaw === 'string') ? JSON.parse(contentRaw) : contentRaw;

        // Aggregate actions
        if (parsedOutput.mene_actions && Array.isArray(parsedOutput.mene_actions)) {
            result.mene_actions.push(...parsedOutput.mene_actions);
        }

        if (parsedOutput.followup_items && Array.isArray(parsedOutput.followup_items)) {
            result.followup_items.push(...parsedOutput.followup_items);
        }

        // Track processed document
        // We assume the original document title is preserved in the JSON flow. 
        // If not, ensure the AI Agent node passes through input variables.
        const docTitle = item.json.title || "Unknown Document";
        result.documents_processed.push(docTitle);

    } catch (error) {
        console.log("Error processing item:", error);
        // You might want to log this or add to an 'errors' array in the result
    }
}

return [{ json: result }];
