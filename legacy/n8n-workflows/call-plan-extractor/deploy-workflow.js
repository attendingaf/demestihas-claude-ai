const fs = require('fs');
const https = require('https');

// Configuration
const N8N_HOST = 'dpsllc.app.n8n.cloud';
const N8N_API_KEY = process.env.N8N_API_KEY;
const WORKFLOW_FILE = './workflow.json';

if (!N8N_API_KEY) {
    console.error('Error: N8N_API_KEY environment variable is not set.');
    console.error('Usage: export N8N_API_KEY="your-api-key" && node deploy-workflow.js');
    process.exit(1);
}

// Read the workflow JSON file
let workflowJson;
try {
    const rawData = fs.readFileSync(WORKFLOW_FILE, 'utf8');
    workflowJson = JSON.parse(rawData);
} catch (err) {
    console.error(`Error reading workflow file: ${err.message}`);
    process.exit(1);
}

// Prepare request options
const options = {
    hostname: N8N_HOST,
    path: '/api/v1/workflows',
    method: 'POST',
    headers: {
        'X-N8N-API-KEY': N8N_API_KEY,
        'Content-Type': 'application/json'
    }
};

const req = https.request(options, (res) => {
    let data = '';

    res.on('data', (chunk) => {
        data += chunk;
    });

    res.on('end', () => {
        if (res.statusCode >= 200 && res.statusCode < 300) {
            const responseBody = JSON.parse(data);
            console.log('✅ Workflow created successfully!');
            console.log(`🆔 Workflow ID: ${responseBody.id}`);
            console.log(`📛 Name: ${responseBody.name}`);
            console.log(`⚠️  Don't forget to activate it in the n8n UI!`);
        } else {
            console.error(`❌ Failed to create workflow. Status Code: ${res.statusCode}`);
            console.error(`Response Class: ${res.headers['content-type']}`);
            console.error(`Response Body: ${data}`);
        }
    });
});

req.on('error', (e) => {
    console.error(`❌ Request error: ${e.message}`);
});

// Write data to request body
req.write(JSON.stringify(workflowJson));
req.end();
