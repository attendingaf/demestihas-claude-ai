import { Server } from '@modelcontextprotocol/sdk/server/index.js';
import { StdioServerTransport } from '@modelcontextprotocol/sdk/server/stdio.js';
import { CallToolRequestSchema, ListToolsRequestSchema } from '@modelcontextprotocol/sdk/types.js';
import { PythonShell } from 'python-shell';
import path from 'path';
import { fileURLToPath } from 'url';

const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);

class PlumaMCPServer {
  constructor() {
    this.server = new Server(
      {
        name: 'pluma-email',
        version: '1.0.0',
      },
      {
        capabilities: {
          tools: {},
        },
      }
    );
    
    this.setupHandlers();
    this.pythonPath = path.join(__dirname, '..', 'python');
  }

  setupHandlers() {
    // List available tools
    this.server.setRequestHandler(ListToolsRequestSchema, async () => ({
      tools: [
        {
          name: 'pluma_fetch_emails',
          description: 'Fetch latest emails from Gmail inbox',
          inputSchema: {
            type: 'object',
            properties: {
              max_results: {
                type: 'number',
                description: 'Maximum number of emails to fetch',
                default: 10
              },
              days_back: {
                type: 'number',
                description: 'Number of days to look back',
                default: 7
              }
            }
          }
        },
        {
          name: 'pluma_generate_reply',
          description: 'Generate a draft reply to an email using Claude',
          inputSchema: {
            type: 'object',
            properties: {
              email_id: {
                type: 'string',
                description: 'ID of the email to reply to'
              },
              instructions: {
                type: 'string',
                description: 'Specific instructions for the reply',
                default: ''
              },
              style: {
                type: 'string',
                enum: ['professional', 'casual', 'brief', 'detailed'],
                description: 'Style of the reply',
                default: 'professional'
              }
            },
            required: ['email_id']
          }
        },
        {
          name: 'pluma_create_draft',
          description: 'Create a Gmail draft from generated reply',
          inputSchema: {
            type: 'object',
            properties: {
              email_id: {
                type: 'string',
                description: 'Original email ID'
              },
              draft_body: {
                type: 'string',
                description: 'Draft reply body text'
              }
            },
            required: ['email_id', 'draft_body']
          }
        },
        {
          name: 'pluma_search_emails',
          description: 'Search emails with Gmail query syntax',
          inputSchema: {
            type: 'object',
            properties: {
              query: {
                type: 'string',
                description: 'Gmail search query'
              },
              max_results: {
                type: 'number',
                description: 'Maximum results to return',
                default: 10
              }
            },
            required: ['query']
          }
        },
        {
          name: 'pluma_get_thread',
          description: 'Get full email thread conversation',
          inputSchema: {
            type: 'object',
            properties: {
              thread_id: {
                type: 'string',
                description: 'Gmail thread ID'
              }
            },
            required: ['thread_id']
          }
        }
      ]
    }));

    // Handle tool calls
    this.server.setRequestHandler(CallToolRequestSchema, async (request) => {
      const { name, arguments: args } = request.params;
      
      try {
        const result = await this.callPython(name, args);
        return {
          content: [
            {
              type: 'text',
              text: typeof result === 'string' ? result : JSON.stringify(result, null, 2)
            }
          ]
        };
      } catch (error) {
        return {
          content: [
            {
              type: 'text',
              text: `Error: ${error.message}`
            }
          ],
          isError: true
        };
      }
    });
  }

  async callPython(method, params) {
    const options = {
      mode: 'json',
      pythonPath: '/Users/menedemestihas/Projects/demestihas-ai/pluma-local/pluma-env/bin/python',
      pythonOptions: ['-u'],
      scriptPath: this.pythonPath,
      args: [JSON.stringify({ method, params })]
    };

    return new Promise((resolve, reject) => {
      PythonShell.run('pluma_bridge.py', options, (err, results) => {
        if (err) reject(err);
        else resolve(results[0]);
      });
    });
  }

  async run() {
    const transport = new StdioServerTransport();
    await this.server.connect(transport);
  }
}

const server = new PlumaMCPServer();
server.run().catch(console.error);
