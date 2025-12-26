#!/usr/bin/env node

/**
 * EA-AI MCP Server for Claude Desktop (Simplified)
 * Works without MCP SDK dependency
 */

const fs = require('fs').promises;
const path = require('path');
const readline = require('readline');
const EABootstrap = require('./bootstrap.js');

class EAAIServerSimple {
  constructor() {
    this.initialized = false;
    this.initializeBootstrap();
  }

  async initializeBootstrap() {
    console.error('Initializing EA-AI Bootstrap (Simplified Mode)...');
    
    try {
      const result = await EABootstrap.init({
        maxLatency: 300,
        fallbackEnabled: true,
        memoryShare: true
      });
      
      console.error(`EA-AI Bootstrap completed in ${result.bootstrapTime}ms`);
      console.error(`Agents ready: ${result.agents.join(', ')}`);
      this.initialized = true;
    } catch (error) {
      console.error('EA-AI Bootstrap failed:', error);
    }
  }

  async handleRequest(request) {
    try {
      const data = JSON.parse(request);
      
      if (data.method === 'tools/list') {
        return this.listTools();
      }
      
      if (data.method === 'tools/call') {
        return await this.callTool(data.params);
      }
      
      return { error: 'Unknown method' };
    } catch (error) {
      return { error: error.message };
    }
  }

  listTools() {
    return {
      tools: [
        {
          name: 'ea_ai_route',
          description: 'Route requests through EA-AI specialized agents',
          inputSchema: {
            type: 'object',
            properties: {
              agent: {
                type: 'string',
                enum: ['pluma', 'huata', 'lyco', 'kairos', 'auto']
              },
              operation: { type: 'string' },
              params: { type: 'object' }
            }
          }
        },
        {
          name: 'ea_ai_memory',
          description: 'Access EA-AI smart memory system',
          inputSchema: {
            type: 'object',
            properties: {
              action: {
                type: 'string',
                enum: ['get', 'set', 'search', 'persist']
              },
              key: { type: 'string' },
              value: { type: 'any' }
            }
          }
        },
        {
          name: 'ea_ai_calendar_check',
          description: 'Check all 6 calendars for conflicts',
          inputSchema: {
            type: 'object',
            properties: {
              action: {
                type: 'string',
                enum: ['check_conflicts', 'find_free_time', 'next_event']
              },
              timeRange: { type: 'object' }
            }
          }
        },
        {
          name: 'ea_ai_task_adhd',
          description: 'ADHD-optimized task management',
          inputSchema: {
            type: 'object',
            properties: {
              task: { type: 'string' },
              action: {
                type: 'string',
                enum: ['break_down', 'prioritize', 'time_block', 'energy_match']
              }
            }
          }
        }
      ]
    };
  }

  async callTool(params) {
    const { name, arguments: args } = params;
    
    switch (name) {
      case 'ea_ai_route':
        return await this.handleRoute(args);
      
      case 'ea_ai_memory':
        return await this.handleMemory(args);
      
      case 'ea_ai_calendar_check':
        return await this.handleCalendarCheck(args);
      
      case 'ea_ai_task_adhd':
        return await this.handleTaskADHD(args);
      
      default:
        return { error: `Unknown tool: ${name}` };
    }
  }

  async handleRoute(args) {
    const { agent, operation, params = {} } = args;
    
    const targetAgent = agent === 'auto' ? 
      this.detectAgent(operation) : agent;
    
    const result = await EABootstrap.routeToAgent(targetAgent, {
      operation,
      ...params
    });
    
    return {
      content: [{
        type: 'text',
        text: JSON.stringify({
          agent: targetAgent,
          result,
          latency: result?.latency || 'N/A'
        }, null, 2)
      }]
    };
  }

  async handleMemory(args) {
    const { action, key, value } = args;
    
    let result;
    switch (action) {
      case 'get':
        result = EABootstrap.memory.get(key);
        break;
      
      case 'set':
        EABootstrap.memory.set(key, value);
        result = { success: true };
        break;
      
      case 'search':
        result = Array.from(EABootstrap.memory.entries())
          .filter(([k, v]) => k.includes(key) || JSON.stringify(v).includes(key));
        break;
      
      case 'persist':
        await EABootstrap.persistMemory();
        result = { persisted: true, items: EABootstrap.memory.size };
        break;
    }
    
    return {
      content: [{
        type: 'text',
        text: JSON.stringify(result, null, 2)
      }]
    };
  }

  async handleCalendarCheck(args) {
    const calendars = [
      'menelaos4@gmail.com',
      'mene@beltlineconsulting.co',
      '7dia35946hir6rbq10stda8hk4@group.calendar.google.com',
      'e46i6ac3ipii8b7iugsqfeh2j8@group.calendar.google.com',
      'c4djl5q698b556jqliablah9uk@group.calendar.google.com',
      'up5jrbrsng5le7qmu0uhi6pedo@group.calendar.google.com'
    ];
    
    return {
      content: [{
        type: 'text',
        text: JSON.stringify({
          action: args.action,
          calendars,
          timeRange: args.timeRange,
          note: 'Calendar integration ready'
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
    }
    
    return {
      content: [{
        type: 'text',
        text: JSON.stringify(result, null, 2)
      }]
    };
  }

  detectAgent(operation) {
    const keywords = {
      pluma: ['email', 'gmail', 'draft', 'reply'],
      huata: ['calendar', 'schedule', 'meeting'],
      lyco: ['task', 'todo', 'priority'],
      kairos: ['time', 'reminder', 'deadline']
    };
    
    for (const [agent, words] of Object.entries(keywords)) {
      if (words.some(word => operation.toLowerCase().includes(word))) {
        return agent;
      }
    }
    
    return 'lyco';
  }

  breakDownTask(task, duration) {
    const chunks = Math.ceil(duration / 15);
    const subtasks = [];
    
    for (let i = 0; i < chunks; i++) {
      subtasks.push({
        chunk: i + 1,
        duration: Math.min(15, duration - (i * 15)),
        description: `${task} - Part ${i + 1}`
      });
    }
    
    return {
      task,
      totalDuration: duration,
      chunks: subtasks,
      adhd_note: 'Broken into 15-minute focus blocks'
    };
  }

  prioritizeTask(task) {
    const urgentKeywords = ['urgent', 'asap', 'emergency', 'critical'];
    const importantKeywords = ['important', 'key', 'vital', 'essential'];
    
    const isUrgent = urgentKeywords.some(word => 
      task.toLowerCase().includes(word));
    const isImportant = importantKeywords.some(word => 
      task.toLowerCase().includes(word));
    
    return {
      task,
      quadrant: isUrgent && isImportant ? 'Q1: Do First' :
                isImportant ? 'Q2: Schedule' :
                isUrgent ? 'Q3: Delegate' : 'Q4: Delete/Defer',
      priority: isUrgent && isImportant ? 'Critical' :
                isImportant ? 'High' :
                isUrgent ? 'Medium' : 'Low'
    };
  }

  timeBlockTask(task, duration) {
    const now = new Date();
    const blocks = [];
    
    for (let i = 0; i < Math.ceil(duration / 15); i++) {
      const blockStart = new Date(now.getTime() + (i * 15 * 60000));
      const blockEnd = new Date(blockStart.getTime() + (15 * 60000));
      
      blocks.push({
        start: blockStart.toISOString(),
        end: blockEnd.toISOString(),
        task: `${task} - Block ${i + 1}`
      });
    }
    
    return {
      task,
      duration,
      blocks,
      strategy: 'Pomodoro-style time blocking'
    };
  }

  matchTaskToEnergy(task) {
    const highEnergyTasks = ['creative', 'strategic', 'complex', 'analysis'];
    const requiresHighEnergy = highEnergyTasks.some(word => 
      task.toLowerCase().includes(word));
    
    return {
      task,
      energyLevel: requiresHighEnergy ? 'High' : 'Low',
      bestTime: requiresHighEnergy ? 'Morning (9-11am)' : 'Afternoon (2-4pm)',
      adhd_tip: requiresHighEnergy ? 
        'Do this when medication is most effective' : 
        'Good for low-focus periods'
    };
  }

  async run() {
    console.error('EA-AI Simplified MCP Server running');
    console.error('Mode: Stdio JSON-RPC');
    
    const rl = readline.createInterface({
      input: process.stdin,
      output: process.stdout,
      terminal: false
    });
    
    rl.on('line', async (line) => {
      try {
        const response = await this.handleRequest(line);
        console.log(JSON.stringify(response));
      } catch (error) {
        console.log(JSON.stringify({ error: error.message }));
      }
    });
  }
}

// Try to load MCP SDK if available, otherwise use simplified version
try {
  const { Server } = require('@modelcontextprotocol/sdk/server/index.js');
  const { StdioServerTransport } = require('@modelcontextprotocol/sdk/server/stdio.js');
  
  // Load the full MCP server
  require('./mcp-server.js');
} catch (error) {
  // MCP SDK not available, use simplified version
  console.error('MCP SDK not found, using simplified server');
  const server = new EAAIServerSimple();
  server.run().catch(console.error);
}
