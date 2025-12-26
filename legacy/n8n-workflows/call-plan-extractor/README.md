# Call Plan Action Item Extractor for n8n

This directory contains the assets and instructions to build the **Call Plan Action Item Extractor** workflow in n8n.

## Objective

Build an n8n workflow that runs daily at 4pm ET, reads call plans modified in the past 7 days from Google Drive, extracts action items using an AI agent (Claude), and surfaces them for review.

## Target Environment

- **n8n Instance**: `https://dpsllc.app.n8n.cloud`
- **Schedule**: Daily at 4:00 PM ET

### Deployment Methods

**Option 1: Programmatic Deployment (Recommended if you have an API Key)**
If you want to deploy this programmatically as requested:

1. Obtain your n8n API Key from **Settings > Public API** in your n8n instance.
2. Run the deployment script:

   ```bash
   export N8N_API_KEY="your-api-key-here"
   node deploy-workflow.js
   ```

**Option 2: Import from File (Easiest)**

1. Open n8n.
2. Click "Add Workflow" > "Import from File".
3. Select the `workflow.json` file contained in this directory.
4. Update the CREDENTIALS placeholders in the nodes.

### Workflow Steps

### Trigger

- **Node Type**: Schedule Trigger
- **Settings**:
  - Trigger Interval: Every Day
  - Hour: 16 (4pm)
  - Minute: 00
  - Timezone: America/New_York

### Step 1: Calculate Date Filter

- **Node Type**: Code (JavaScript)
- **Source Code**: Copy content from `step1-date-filter.js`
- **Purpose**: Generates an ISO timestamp for 7 days ago (`dateFilter`).

### Step 2: Search Google Drive

- **Node Type**: Google Drive
- **Operation**: Search Files and Folders
- **Query**:

  ```text
  name contains 'Call Plan' and mimeType = 'application/vnd.google-apps.document' and modifiedTime > '{{$json.dateFilter}}'
  ```

- **Credentials**: Google Drive OAuth2
- **Note**: Ensure the Credentials have `drive.readonly`.

### Step 3: Loop Over Documents

- **Node Type**: Loop Over Items
- **Batch Size**: 1
- **Input**: Output from Step 2 (List of files)

### Step 4: Fetch Document Content

- **Node Type**: Google Docs
- **Operation**: Get Document Content
- **Document ID**: `{{$json.id}}` (Expression mapping from Step 3)
- **Output Format**: Plain text

### Step 5: AI Agent - Extract Action Items

- **Node Type**: AI Agent (or HTTP Request to Claude API)
- **Model**: `claude-sonnet-4-20250514` (Ensure this model ID is valid in your n8n version, or use `claude-3-sonnet...`)
- **Credentials**: Anthropic API Key
- **System Prompt**: Copy content from `step5-system-prompt.txt`
  - *Note: The prompt has been optimized to request JSON output.*
- **User Prompt**:

  ```text
  Document: {{$json.title}}
  
  Content:
  {{$json.content}}
  ```

### Step 6: Aggregate Results

- **Node Type**: Code (JavaScript)
- **Source Code**: Copy content from `step6-aggregation.js`
- **Purpose**: Combines results from all looped items into a single JSON report.
- **Important**: ensure this node runs after the Loop finishes or is connected to the Loop's "Done" output (depending on n8n version/loop style). If using "Split in Batches", you might need a customized aggregation pattern.

### Step 7: Output (Choose One)

- **Option A (Email)**: Send Email node to `menelaos4@gmail.com`.
  - Subject: `Call Plan Action Items - {{$json.run_timestamp}}`
  - Body: Use an HTML list or formatting based on `mene_actions` and `followup_items`.
- **Option B (Tasks)**: Google Tasks node.
  - Loop over `mene_actions` to create individual tasks.

## Environment Variables / Credentials

- `ANTHROPIC_API_KEY`: Required for Step 5.
- Google OAuth2 Credentials: Required for Steps 2 & 4.
  - Scopes: `https://www.googleapis.com/auth/drive.readonly`, `https://www.googleapis.com/auth/documents.readonly`.

## Testing

1. Manually trigger the workflow.
2. Verify the Google Drive search finds files (ensure you have a test file modified in the last 7 days).
3. Check that the AI Agent returns valid JSON.
4. Verify the Aggregation node produces the final `mene_actions` list.

## Error Handling

- Add an **Error Trigger** node to the workflow canvas.
- Connect it to a notification node (Email or Slack) to alert you if the workflow fails.
- Configure it to log the execution ID or specific error message.
