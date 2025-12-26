require('dotenv').config();
const express = require('express');
const bodyParser = require('body-parser');
const cors = require('cors');
const { McpServer, ResourceTemplate } = require('@modelcontextprotocol/sdk/server/mcp.js');
const { SSEServerTransport } = require('@modelcontextprotocol/sdk/server/sse.js');
const linkedInClient = require('./linkedin');

const app = express();
const PORT = process.env.PORT || 3000;

app.use(cors());
app.use(bodyParser.json());

// Initialize MCP Server
const mcp = new McpServer({
    name: "LinkedIn MCP Server",
    version: "1.0.0"
});

// Define Tools
mcp.tool("post_text",
    { text: { type: "string", description: "Text content of the post" } },
    async ({ text }) => {
        try {
            const result = await linkedInClient.postText(text);
            return { content: [{ type: "text", text: `Successfully posted text: ${JSON.stringify(result)}` }] };
        } catch (error) {
            return { content: [{ type: "text", text: `Error: ${error.message}` }], isError: true };
        }
    }
);

mcp.tool("post_article",
    {
        text: { type: "string", description: "Text commentary" },
        url: { type: "string", description: "URL of the article to share" }
    },
    async ({ text, url }) => {
        try {
            const result = await linkedInClient.postArticle(text, url);
            return { content: [{ type: "text", text: `Successfully posted article: ${JSON.stringify(result)}` }] };
        } catch (error) {
            return { content: [{ type: "text", text: `Error: ${error.message}` }], isError: true };
        }
    }
);

mcp.tool("post_image",
    {
        text: { type: "string", description: "Text commentary" },
        image_path: { type: "string", description: "Local path to the image file on the server" }
    },
    async ({ text, image_path }) => {
        try {
            const result = await linkedInClient.postImage(text, image_path);
            return { content: [{ type: "text", text: `Successfully posted image: ${JSON.stringify(result)}` }] };
        } catch (error) {
            return { content: [{ type: "text", text: `Error: ${error.message}` }], isError: true };
        }
    }
);

// OAuth Endpoints
app.get('/auth/linkedin', (req, res) => {
    res.redirect(linkedInClient.getAuthUrl());
});

app.get('/auth/linkedin/callback', async (req, res) => {
    const { code } = req.query;
    if (!code) {
        return res.status(400).send('No code provided');
    }
    try {
        await linkedInClient.exchangeToken(code);
        res.send('Authentication successful! You can now use the LinkedIn tools.');
    } catch (error) {
        res.status(500).send(`Authentication failed: ${error.message}`);
    }
});

// REST Endpoints for Tools (Wrappers)
app.post('/api/post_text', async (req, res) => {
    const { text } = req.body;
    if (!text) return res.status(400).json({ error: 'Text is required' });
    try {
        const result = await linkedInClient.postText(text);
        res.json(result);
    } catch (error) {
        res.status(500).json({ error: error.message });
    }
});

app.post('/api/post_article', async (req, res) => {
    const { text, url } = req.body;
    if (!text || !url) return res.status(400).json({ error: 'Text and URL are required' });
    try {
        const result = await linkedInClient.postArticle(text, url);
        res.json(result);
    } catch (error) {
        res.status(500).json({ error: error.message });
    }
});

app.post('/api/post_image', async (req, res) => {
    const { text, image_path } = req.body;
    if (!text || !image_path) return res.status(400).json({ error: 'Text and image_path are required' });
    try {
        const result = await linkedInClient.postImage(text, image_path);
        res.json(result);
    } catch (error) {
        res.status(500).json({ error: error.message });
    }
});

// Health Check
app.get('/health', (req, res) => {
    res.json({ status: 'healthy', timestamp: new Date().toISOString() });
});

// MCP SSE Endpoint
let transport;
app.get('/sse', async (req, res) => {
    transport = new SSEServerTransport("/messages", res);
    await mcp.connect(transport);
});

app.post('/messages', async (req, res) => {
    if (transport) {
        await transport.handlePostMessage(req, res);
    } else {
        res.status(404).send("Session not found");
    }
});

app.listen(PORT, () => {
    console.log(`LinkedIn MCP Server running on port ${PORT}`);
    console.log(`Auth URL: http://localhost:${PORT}/auth/linkedin`);
});
