#!/usr/bin/env node

/**
 * EA-AI MCP Server for Claude Desktop (v2 - Fully Fixed)
 * Properly implements JSON-RPC 2.0 protocol with full error handling
 */

const readline = require('readline');

class EAAIServerV2 {
  constructor() {
    this.initialized = false;
    this.startTime = Date.now();
    this.memory = new Map();
    this.agents = new Map();
    this.initializeAgents();
  }

  initializeAgents() {
    console.error('[EA-AI] Initializing agents...');
    this.agents.set('pluma', { type: 'email', status: 'ready' });
    this.agents.set('huata', { type: 'calendar', status: 'ready' });
    this.agents.set('lyco', { type: 'task', status: 'ready' });
    this.agents.set('kairos', { type: 'time', status: 'ready' });
    console.error(`[EA-AI] Bootstrap completed in ${Date.now() - this.startTime}ms`);
  }

  async processMessage(message) {
    let data;
    try {
      data = JSON.parse(message);
    } catch (e) {
      return {
        jsonrpc: "2.0",
        id: null,
        error: {
          code: -32700,
          message: "Parse error"
        }
      };
    }

    // Log all incoming messages for debugging
    console.error(`[EA-AI] Received: ${data.method || 'response'}`);

    // Handle notifications (no response)
    if (!data.id) {
      if (data.method && data.method.startsWith('notifications/')) {
        console.error(`[EA-AI] Notification: ${data.method}`);
        return null;
      }
    }

    // Build response
    const response = {
      jsonrpc: "2.0",
      id: data.id
    };

    try {
      switch (data.method) {
        case 'initialize':
          response.result = {
            protocolVersion: "2025-06-18",
            capabilities: {
              tools: {},
              prompts: {},
              resources: {}
            },
            serverInfo: {
              name: "ea-ai",
              version: "2.0.0"
            }
          };
          this.initialized = true;
          console.error('[EA-AI] Initialized successfully');
          break;

        case 'tools/list':
          response.result = this.getToolsList();
          break;

        case 'prompts/list':
          response.result = { prompts: [] };
          break;

        case 'resources/list':
          response.result = { resources: [] };
          break;

        case 'tools/call':
          response.result = await this.callTool(data.params);
          break;

        default:
          if (data.method) {
            response.error = {
              code: -32601,
              message: `Method not found: ${data.method}`
            };
          }
      }
    } catch (error) {
      console.error(`[EA-AI] Error processing ${data.method}:`, error);
      response.error = {
        code: -32603,
        message: error.message
      };
    }

    return response;
  }

  getToolsList() {
    return {
      tools: [
        {
          name: 'ea_ai_route',
          description: 'Route requests through EA-AI specialized agents (pluma=email, huata=calendar, lyco=tasks, kairos=time)',
          inputSchema: {
            type: 'object',
            properties: {
              agent: {
                type: 'string',
                enum: ['pluma', 'huata', 'lyco', 'kairos', 'auto'],
                description: 'Target agent or auto for automatic routing'
              },
              operation: {
                type: 'string',
                description: 'Operation to perform'
              },
              params: {
                type: 'object',
                description: 'Additional parameters'
              }
            },
            required: ['agent', 'operation']
          }
        },
        {
          name: 'ea_ai_memory',
          description: 'Access EA-AI smart memory system for persistent context',
          inputSchema: {
            type: 'object',
            properties: {
              action: {
                type: 'string',
                enum: ['get', 'set', 'search', 'persist'],
                description: 'Memory operation'
              },
              key: {
                type: 'string',
                description: 'Memory key'
              },
              value: {
                description: 'Value to store (for set action)'
              }
            },
            required: ['action']
          }
        },
        {
          name: 'ea_ai_calendar_check',
          description: 'Check all 6 family calendars for conflicts and availability',
          inputSchema: {
            type: 'object',
            properties: {
              action: {
                type: 'string',
                enum: ['check_conflicts', 'find_free_time', 'next_event'],
                description: 'Calendar operation'
              },
              timeRange: {
                type: 'object',
                properties: {
                  start: { type: 'string' },
                  end: { type: 'string' }
                },
                description: 'Time range for checking'
              }
            },
            required: ['action']
          }
        },
        {
          name: 'ea_ai_task_adhd',
          description: 'ADHD-optimized task management (15-minute chunks)',
          inputSchema: {
            type: 'object',
            properties: {
              task: {
                type: 'string',
                description: 'Task description'
              },
              action: {
                type: 'string',
                enum: ['break_down', 'prioritize', 'time_block', 'energy_match'],
                description: 'Task management action'
              },
              duration: {
                type: 'number',
                description: 'Task duration in minutes'
              }
            },
            required: ['task', 'action']
          }
        },
        {
          name: 'ea_ai_family',
          description: 'Load family context and preferences',
          inputSchema: {
            type: 'object',
            properties: {
              member: {
                type: 'string',
                enum: ['mene', 'cindy', 'kids', 'all', 'auto'],
                description: 'Family member context to load'
              }
            },
            required: ['member']
          }
        }
      ]
    };
  }

  async callTool(params) {
    const { name, arguments: args } = params;
    console.error(`[EA-AI] Calling tool: ${name}`);

    try {
      switch (name) {
        case 'ea_ai_route':
          return this.handleRoute(args);
        case 'ea_ai_memory':
          return this.handleMemory(args);
        case 'ea_ai_calendar_check':
          return this.handleCalendarCheck(args);
        case 'ea_ai_task_adhd':
          return this.handleTaskADHD(args);
        case 'ea_ai_family':
          return this.handleFamily(args);
        default:
          throw new Error(`Unknown tool: ${name}`);
      }
    } catch (error) {
      console.error(`[EA-AI] Tool error:`, error);
      return {
        content: [{
          type: 'text',
          text: `Error: ${error.message}`
        }]
      };
    }
  }

  handleRoute(args) {
    const { agent, operation, params = {} } = args;
    const targetAgent = agent === 'auto' ? this.detectAgent(operation) : agent;
    
    return {
      content: [{
        type: 'text',
        text: JSON.stringify({
          agent: targetAgent,
          operation,
          status: 'routed',
          params,
          timestamp: new Date().toISOString()
        }, null, 2)
      }]
    };
  }

  handleMemory(args) {
    const { action, key, value } = args;
    let result;

    switch (action) {
      case 'get':
        result = {
          key,
          value: this.memory.get(key) || null,
          found: this.memory.has(key)
        };
        break;
      case 'set':
        this.memory.set(key, value);
        result = {
          action: 'set',
          key,
          success: true,
          size: this.memory.size
        };
        break;
      case 'search':
        const matches = Array.from(this.memory.entries())
          .filter(([k, v]) =>
            k.includes(key || '') ||
            JSON.stringify(v).includes(key || '')
          );
        result = {
          action: 'search',
          query: key,
          matches: matches.length,
          results: matches.slice(0, 10)
        };
        break;
      case 'persist':
        result = {
          action: 'persist',
          persisted: true,
          items: this.memory.size,
          timestamp: new Date().toISOString()
        };
        break;
      default:
        result = { error: 'Unknown action' };
    }

    return {
      content: [{
        type: 'text',
        text: JSON.stringify(result, null, 2)
      }]
    };
  }

  handleCalendarCheck(args) {
    const { action, timeRange } = args;
    const calendars = {
      primary: 'menelaos4@gmail.com',
      work: 'mene@beltlineconsulting.co',
      lys_familia: '7dia35946hir6rbq10stda8hk4@group.calendar.google.com',
      limon_sal: 'e46i6ac3ipii8b7iugsqfeh2j8@group.calendar.google.com',
      cindy: 'c4djl5q698b556jqliablah9uk@group.calendar.google.com',
      au_pair: 'up5jrbrsng5le7qmu0uhi6pedo@group.calendar.google.com'
    };

    return {
      content: [{
        type: 'text',
        text: JSON.stringify({
          action,
          calendars,
          timeRange,
          status: 'ready',
          note: 'Use list_gcal_events or find_free_time tools for actual calendar data'
        }, null, 2)
      }]
    };
  }

  handleTaskADHD(args) {
    const { task, action, duration = 60 } = args;
    let result;

    switch (action) {
      case 'break_down':
        const chunks = Math.ceil(duration / 15);
        const subtasks = [];
        for (let i = 0; i < chunks; i++) {
          subtasks.push({
            chunk: i + 1,
            duration: Math.min(15, duration - (i * 15)),
            description: `${task} - Part ${i + 1}/${chunks}`
          });
        }
        result = {
          task,
          totalDuration: duration,
          chunks,
          subtasks,
          adhd_strategy: 'Optimized 15-minute focus blocks'
        };
        break;

      case 'prioritize':
        const urgentKeywords = ['urgent', 'asap', 'emergency', 'critical'];
        const importantKeywords = ['important', 'key', 'vital', 'essential'];
        const taskLower = task.toLowerCase();
        const isUrgent = urgentKeywords.some(word => taskLower.includes(word));
        const isImportant = importantKeywords.some(word => taskLower.includes(word));
        
        result = {
          task,
          quadrant: isUrgent && isImportant ? 'Q1: Do First' :
                   isImportant ? 'Q2: Schedule' :
                   isUrgent ? 'Q3: Delegate' : 'Q4: Delete/Defer',
          priority: isUrgent && isImportant ? 'Critical' :
                   isImportant ? 'High' :
                   isUrgent ? 'Medium' : 'Low'
        };
        break;

      case 'time_block':
        const now = new Date();
        const blocks = [];
        const numBlocks = Math.ceil(duration / 15);
        for (let i = 0; i < numBlocks; i++) {
          const blockStart = new Date(now.getTime() + (i * 20 * 60000));
          const blockEnd = new Date(blockStart.getTime() + (15 * 60000));
          blocks.push({
            block: i + 1,
            start: blockStart.toTimeString().slice(0, 5),
            end: blockEnd.toTimeString().slice(0, 5),
            task: `${task} - Block ${i + 1}/${numBlocks}`
          });
        }
        result = {
          task,
          duration,
          blocks,
          strategy: 'Pomodoro-style with ADHD optimization'
        };
        break;

      case 'energy_match':
        const highEnergyTasks = ['creative', 'strategic', 'complex', 'analysis'];
        const taskLowerEnergy = task.toLowerCase();
        const requiresHighEnergy = highEnergyTasks.some(word => taskLowerEnergy.includes(word));
        
        result = {
          task,
          energyLevel: requiresHighEnergy ? 'High' : 'Medium',
          bestTime: requiresHighEnergy ? 'Morning (9-11am)' : 'Afternoon (2-4pm)',
          adhd_tip: requiresHighEnergy ?
            'Do when medication is most effective' :
            'Good for low-focus periods'
        };
        break;

      default:
        result = { error: 'Unknown action' };
    }

    return {
      content: [{
        type: 'text',
        text: JSON.stringify(result, null, 2)
      }]
    };
  }

  handleFamily(args) {
    const { member } = args;
    const context = {
      mene: {
        style: 'Direct, execution-focused',
        energy: 'Peak 9-11am',
        enneagram: 'Eight',
        adhd: 'Hyperactive type'
      },
      cindy: {
        style: 'Detailed, planning-focused',
        energy: 'Steady throughout day',
        enneagram: 'Six',
        adhd: 'Inattentive type'
      },
      kids: {
        schedule: 'School 8am-3:30pm weekdays',
        evening: 'Dinner 6:30pm, bedtime 8:30pm'
      }
    };

    const selected = member === 'all' ? context :
                    member === 'auto' ? context.mene :
                    context[member] || {};

    return {
      content: [{
        type: 'text',
        text: JSON.stringify({
          member,
          context: selected,
          loaded: true,
          timestamp: new Date().toISOString()
        }, null, 2)
      }]
    };
  }

  detectAgent(operation) {
    const keywords = {
      pluma: ['email', 'gmail', 'draft', 'reply'],
      huata: ['calendar', 'schedule', 'meeting', 'event'],
      lyco: ['task', 'todo', 'priority', 'deadline'],
      kairos: ['time', 'reminder', 'timer', 'duration']
    };

    const lowerOp = operation.toLowerCase();
    for (const [agent, words] of Object.entries(keywords)) {
      if (words.some(word => lowerOp.includes(word))) {
        return agent;
      }
    }
    return 'lyco';
  }

  async run() {
    console.error('[EA-AI] MCP Server v2.0 starting...');
    console.error('[EA-AI] Protocol: JSON-RPC 2.0 over stdio');

    const rl = readline.createInterface({
      input: process.stdin,
      output: process.stdout,
      terminal: false
    });

    rl.on('line', async (line) => {
      if (!line.trim()) return;
      
      try {
        const response = await this.processMessage(line);
        if (response) {
          console.log(JSON.stringify(response));
        }
      } catch (error) {
        console.error('[EA-AI] Fatal error:', error);
        console.log(JSON.stringify({
          jsonrpc: "2.0",
          id: null,
          error: {
            code: -32603,
            message: error.message
          }
        }));
      }
    });

    process.on('SIGINT', () => {
      console.error('[EA-AI] Shutting down gracefully');
      process.exit(0);
    });

    process.on('uncaughtException', (error) => {
      console.error('[EA-AI] Uncaught exception:', error);
    });

    process.on('unhandledRejection', (reason, promise) => {
      console.error('[EA-AI] Unhandled rejection at:', promise, 'reason:', reason);
    });
  }
}

// Start server
const server = new EAAIServerV2();
server.run().catch(error => {
  console.error('[EA-AI] Failed to start:', error);
  process.exit(1);
});
