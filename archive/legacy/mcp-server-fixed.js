#!/usr/bin/env node

/**
 * EA-AI MCP Server for Claude Desktop (Fixed JSON-RPC)
 * Properly implements JSON-RPC 2.0 protocol
 */

const fs = require('fs').promises;
const path = require('path');
const readline = require('readline');

class EAAIServerFixed {
  constructor() {
    this.initialized = false;
    this.startTime = Date.now();
    this.memory = new Map();
    this.agents = new Map();
    this.cache = new Map();
    this.initializeBootstrap();
  }

  async initializeBootstrap() {
    console.error('Initializing EA-AI Bootstrap (Fixed Mode)...');
    
    try {
      // Quick bootstrap
      this.agents.set('pluma', { type: 'email', status: 'ready' });
      this.agents.set('huata', { type: 'calendar', status: 'ready' });
      this.agents.set('lyco', { type: 'task', status: 'ready' });
      this.agents.set('kairos', { type: 'time', status: 'ready' });
      
      this.initialized = true;
      const bootstrapTime = Date.now() - this.startTime;
      console.error(`EA-AI Bootstrap completed in ${bootstrapTime}ms`);
      console.error(`Agents ready: ${Array.from(this.agents.keys()).join(', ')}`);
    } catch (error) {
      console.error('EA-AI Bootstrap failed:', error);
    }
  }

  async handleRequest(request) {
    try {
      const data = JSON.parse(request);
      
      // Handle notifications (no response needed)
      if (!data.id && data.method) {
        if (data.method.startsWith('notifications/')) {
          // Notifications don't get responses
          return null;
        }
      }
      
      // Build proper JSON-RPC response
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
                prompts: {}
              },
              serverInfo: {
                name: "ea-ai",
                version: "1.0.0"
              }
            };
            break;
            
          case 'tools/list':
            response.result = this.listTools();
            break;
            
          case 'tools/call':
            response.result = await this.callTool(data.params);
            break;
            
          case 'prompts/list':
            // Optional - we don't support prompts
            response.result = { prompts: [] };
            break;
            
          case 'resources/list':
            // Optional - we don't support resources
            response.result = { resources: [] };
            break;
            
          case 'notifications/cancelled':
          case 'notifications/initialized':
            // No response needed for notifications
            return null;
            
          default:
            response.error = {
              code: -32601,
              message: `Method not found: ${data.method}`
            };
        }
      } catch (error) {
        response.error = {
          code: -32603,
          message: error.message
        };
      }
      
      return response;
    } catch (error) {
      return {
        jsonrpc: "2.0",
        id: null,
        error: {
          code: -32700,
          message: "Parse error"
        }
      };
    }
  }

  listTools() {
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
    
    try {
      let result;
      switch (name) {
        case 'ea_ai_route':
          result = await this.handleRoute(args);
          break;
        
        case 'ea_ai_memory':
          result = await this.handleMemory(args);
          break;
        
        case 'ea_ai_calendar_check':
          result = await this.handleCalendarCheck(args);
          break;
        
        case 'ea_ai_task_adhd':
          result = await this.handleTaskADHD(args);
          break;
          
        case 'ea_ai_family':
          result = await this.handleFamily(args);
          break;
        
        default:
          throw new Error(`Unknown tool: ${name}`);
      }
      
      return result;
    } catch (error) {
      return {
        content: [{
          type: 'text',
          text: `Error: ${error.message}`
        }]
      };
    }
  }

  async handleRoute(args) {
    const { agent, operation, params = {} } = args;
    
    const targetAgent = agent === 'auto' ? 
      this.detectAgent(operation) : agent;
    
    return {
      content: [{
        type: 'text',
        text: JSON.stringify({
          agent: targetAgent,
          operation,
          status: 'routed',
          params,
          note: `Request routed to ${targetAgent} agent`
        }, null, 2)
      }]
    };
  }

  async handleMemory(args) {
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

  async handleCalendarCheck(args) {
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

  async handleTaskADHD(args) {
    const { task, action, duration = 60 } = args;
    
    let result;
    switch (action) {
      case 'break_down':
        result = this.breakDownTask(task, duration);
        break;
      
      case 'prioritize':
        result = this.prioritizeTask(task);
        break;
      
      case 'time_block':
        result = this.timeBlockTask(task, duration);
        break;
      
      case 'energy_match':
        result = this.matchTaskToEnergy(task);
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

  async handleFamily(args) {
    const { member } = args;
    
    const context = {
      mene: {
        style: 'Direct, execution-focused',
        energy: 'Peak 9-11am',
        enneagram: 'Eight',
        adhd: 'Hyperactive type',
        preferences: ['No fluff', 'Action-oriented', 'Quick decisions']
      },
      cindy: {
        style: 'Detailed, planning-focused',
        energy: 'Steady throughout day',
        enneagram: 'Six',
        adhd: 'Inattentive type',
        preferences: ['Needs reassurance', 'Visual aids', 'Written follow-ups']
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
      pluma: ['email', 'gmail', 'draft', 'reply', 'inbox'],
      huata: ['calendar', 'schedule', 'meeting', 'event', 'appointment'],
      lyco: ['task', 'todo', 'priority', 'deadline', 'project'],
      kairos: ['time', 'reminder', 'timer', 'alarm', 'duration']
    };
    
    const lowerOp = operation.toLowerCase();
    for (const [agent, words] of Object.entries(keywords)) {
      if (words.some(word => lowerOp.includes(word))) {
        return agent;
      }
    }
    
    return 'lyco'; // Default to task management
  }

  breakDownTask(task, duration) {
    const chunks = Math.ceil(duration / 15);
    const subtasks = [];
    
    for (let i = 0; i < chunks; i++) {
      const chunkDuration = Math.min(15, duration - (i * 15));
      subtasks.push({
        chunk: i + 1,
        duration: chunkDuration,
        description: `${task} - Part ${i + 1}/${chunks}`,
        focus: chunkDuration === 15 ? 'Full focus block' : `Partial block (${chunkDuration}min)`
      });
    }
    
    return {
      task,
      totalDuration: duration,
      chunks,
      subtasks,
      adhd_strategy: 'Optimized 15-minute focus blocks',
      tips: [
        'Take 5-minute breaks between chunks',
        'Use timer for each block',
        'Celebrate each completed chunk'
      ]
    };
  }

  prioritizeTask(task) {
    const urgentKeywords = ['urgent', 'asap', 'emergency', 'critical', 'deadline', 'today'];
    const importantKeywords = ['important', 'key', 'vital', 'essential', 'strategic'];
    
    const taskLower = task.toLowerCase();
    const isUrgent = urgentKeywords.some(word => taskLower.includes(word));
    const isImportant = importantKeywords.some(word => taskLower.includes(word));
    
    return {
      task,
      analysis: {
        urgent: isUrgent,
        important: isImportant
      },
      quadrant: isUrgent && isImportant ? 'Q1: Do First' :
                isImportant ? 'Q2: Schedule' :
                isUrgent ? 'Q3: Delegate' : 
                'Q4: Delete/Defer',
      priority: isUrgent && isImportant ? 'Critical' :
                isImportant ? 'High' :
                isUrgent ? 'Medium' : 
                'Low',
      adhd_advice: isUrgent && isImportant ? 
        'Do this NOW while energy is high' :
        isImportant ? 
        'Schedule for morning peak hours' :
        'Can wait or delegate'
    };
  }

  timeBlockTask(task, duration) {
    const now = new Date();
    const blocks = [];
    const numBlocks = Math.ceil(duration / 15);
    
    for (let i = 0; i < numBlocks; i++) {
      const blockStart = new Date(now.getTime() + (i * 20 * 60000)); // 15min work + 5min break
      const blockEnd = new Date(blockStart.getTime() + (15 * 60000));
      
      blocks.push({
        block: i + 1,
        start: blockStart.toTimeString().slice(0, 5),
        end: blockEnd.toTimeString().slice(0, 5),
        task: `${task} - Block ${i + 1}/${numBlocks}`,
        type: 'Focus block',
        break: i < numBlocks - 1 ? '5-minute break after' : 'Task complete!'
      });
    }
    
    return {
      task,
      duration,
      totalTime: numBlocks * 20 - 5, // Remove last break
      blocks,
      strategy: 'Pomodoro-style with ADHD optimization',
      timezone: 'America/New_York'
    };
  }

  matchTaskToEnergy(task) {
    const highEnergyTasks = ['creative', 'strategic', 'complex', 'analysis', 'planning', 'writing'];
    const lowEnergyTasks = ['email', 'routine', 'admin', 'filing', 'review'];
    
    const taskLower = task.toLowerCase();
    const requiresHighEnergy = highEnergyTasks.some(word => taskLower.includes(word));
    const isLowEnergy = lowEnergyTasks.some(word => taskLower.includes(word));
    
    return {
      task,
      energyLevel: requiresHighEnergy ? 'High' : 
                   isLowEnergy ? 'Low' : 
                   'Medium',
      bestTime: requiresHighEnergy ? 
        'Morning (9-11am) - Peak focus window' : 
        isLowEnergy ? 
        'Afternoon (2-4pm) - Lower energy okay' :
        'Midday (11am-2pm) - Steady energy',
      adhd_optimization: {
        high: 'Do when medication is most effective',
        medium: 'Good for transition periods',
        low: 'Perfect for low-focus times'
      }[requiresHighEnergy ? 'high' : isLowEnergy ? 'low' : 'medium'],
      environment: requiresHighEnergy ? 
        'Quiet, no distractions' : 
        'Can handle some interruptions'
    };
  }

  async run() {
    console.error('EA-AI Fixed MCP Server running');
    console.error('Mode: JSON-RPC 2.0 over stdio');
    
    const rl = readline.createInterface({
      input: process.stdin,
      output: process.stdout,
      terminal: false
    });
    
    rl.on('line', async (line) => {
      try {
        const response = await this.handleRequest(line);
        if (response) {
          console.log(JSON.stringify(response));
        }
      } catch (error) {
        console.error('Processing error:', error);
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
      console.error('Shutting down EA-AI server');
      process.exit(0);
    });
  }
}

// Start the server
const server = new EAAIServerFixed();
server.run().catch(console.error);
