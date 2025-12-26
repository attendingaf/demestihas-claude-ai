#!/usr/bin/env node
/**
 * Lyco MCP Server
 * Direct task management integration for Claude Desktop
 */

import { Server } from '@modelcontextprotocol/sdk/server/index.js';
import { StdioServerTransport } from '@modelcontextprotocol/sdk/server/stdio.js';
import {
  CallToolRequestSchema,
  ListToolsRequestSchema,
  McpError,
  ErrorCode
} from '@modelcontextprotocol/sdk/types.js';
import axios from 'axios';
import dotenv from 'dotenv';

dotenv.config();

class LycoMCPServer {
  constructor() {
    this.server = new Server({
      name: 'lyco-task-manager',
      version: '2.0.0'
    }, {
      capabilities: {
        tools: {}
      }
    });

    this.lycoUrl = process.env.LYCO_URL || 'http://localhost:8000';
    this.setupTools();
  }

  setupTools() {
    // Register tool listing handler
    this.server.setRequestHandler(ListToolsRequestSchema, async () => ({
      tools: [
        {
          name: 'lyco_next_task',
          description: 'Get your next task based on current energy and context. Returns the highest priority task optimized for ADHD with clear next action.',
          inputSchema: {
            type: 'object',
            properties: {
              energy_level: {
                type: 'string',
                enum: ['high', 'medium', 'low'],
                description: 'Current energy level (optional, auto-detected if not provided)'
              },
              context: {
                type: 'string',
                description: 'Additional context about current situation (optional)'
              }
            }
          }
        },
        {
          name: 'lyco_complete_task',
          description: 'Mark a task as complete and get the next task',
          inputSchema: {
            type: 'object',
            properties: {
              task_id: {
                type: 'string',
                description: 'Task ID to complete'
              }
            },
            required: ['task_id']
          }
        },
        {
          name: 'lyco_skip_task',
          description: 'Skip a task with intelligent handling based on the reason',
          inputSchema: {
            type: 'object',
            properties: {
              task_id: {
                type: 'string',
                description: 'Task ID to skip'
              },
              reason: {
                type: 'string',
                enum: ['wrong-time', 'need-someone', 'not-now', 'not-important', 'low-energy'],
                description: 'Reason for skipping (triggers intelligent rescheduling)'
              }
            },
            required: ['task_id', 'reason']
          }
        },
        {
          name: 'lyco_start_rounds',
          description: 'Start rapid task decision rounds - quickly process multiple tasks with yes/no decisions',
          inputSchema: {
            type: 'object',
            properties: {
              type: {
                type: 'string',
                enum: ['morning', 'afternoon', 'evening', 'quick'],
                description: 'Type of rounds session (default: quick)'
              }
            }
          }
        },
        {
          name: 'lyco_capture_task',
          description: 'Capture a new task or thought for intelligent processing',
          inputSchema: {
            type: 'object',
            properties: {
              signal: {
                type: 'string',
                description: 'Task description or thought to capture'
              },
              context: {
                type: 'string',
                description: 'Additional context like project, deadline, or energy needed (optional)'
              }
            },
            required: ['signal']
          }
        },
        {
          name: 'lyco_get_queue',
          description: 'Get a preview of upcoming tasks in the queue',
          inputSchema: {
            type: 'object',
            properties: {
              count: {
                type: 'number',
                description: 'Number of tasks to preview (default: 5)'
              }
            }
          }
        },
        {
          name: 'lyco_weekly_review',
          description: 'Generate weekly review with insights and patterns',
          inputSchema: {
            type: 'object',
            properties: {}
          }
        },
        {
          name: 'lyco_update_energy',
          description: 'Update current energy level for better task matching',
          inputSchema: {
            type: 'object',
            properties: {
              level: {
                type: 'string',
                enum: ['high', 'medium', 'low'],
                description: 'Current energy level'
              }
            },
            required: ['level']
          }
        },
        {
          name: 'lyco_get_patterns',
          description: 'Get learned behavior patterns and insights',
          inputSchema: {
            type: 'object',
            properties: {}
          }
        },
        {
          name: 'lyco_status',
          description: 'Get current Lyco system status and metrics',
          inputSchema: {
            type: 'object',
            properties: {}
          }
        }
      ]
    }));

    // Handle tool execution
    this.server.setRequestHandler(CallToolRequestSchema, async (request) => {
      const { name, arguments: args } = request.params;

      try {
        const response = await this.executeTool(name, args || {});
        return {
          content: [{
            type: 'text',
            text: typeof response === 'string'
              ? response
              : JSON.stringify(response, null, 2)
          }]
        };
      } catch (error) {
        console.error(`Tool execution error: ${error.message}`);
        throw new McpError(
          ErrorCode.InternalError,
          `Lyco operation failed: ${error.message}`
        );
      }
    });
  }

  async executeTool(toolName, args) {
    const client = axios.create({
      baseURL: this.lycoUrl,
      timeout: 5000,
      headers: {
        'Content-Type': 'application/json'
      }
    });

    try {
      switch (toolName) {
        case 'lyco_next_task': {
          const params = {};
          if (args.energy_level) params.energy = args.energy_level;

          const { data } = await client.get('/api/next-task', { params });

          if (!data || Object.keys(data).length === 0) {
            return "No tasks available. Great job staying on top of things!";
          }

          return this.formatTask(data);
        }

        case 'lyco_complete_task': {
          const { data: completeData } = await client.post(
            `/api/tasks/${args.task_id}/complete`
          );

          // Get next task automatically
          const { data: nextTask } = await client.get('/api/next-task');

          if (nextTask && Object.keys(nextTask).length > 0) {
            return `✅ Task completed!\n\n**Next Task:**\n${this.formatTask(nextTask)}`;
          } else {
            return "✅ Task completed! No more tasks in queue.";
          }
        }

        case 'lyco_skip_task': {
          const { data } = await client.post(
            `/api/tasks/${args.task_id}/skip`,
            { reason: args.reason }
          );

          const actionMessage = this.getSkipMessage(args.reason, data);

          // Get next task
          const { data: nextTask } = await client.get('/api/next-task');

          if (nextTask && Object.keys(nextTask).length > 0) {
            return `${actionMessage}\n\n**Next Task:**\n${this.formatTask(nextTask)}`;
          } else {
            return `${actionMessage}\n\nNo more tasks in queue.`;
          }
        }

        case 'lyco_start_rounds': {
          const { data } = await client.post('/api/rounds/start', {
            type: args.type || 'quick'
          });

          return this.formatRoundsSession(data);
        }

        case 'lyco_capture_task': {
          const { data } = await client.post('/api/signals', {
            signal: args.signal,
            context: args.context
          });

          return `📝 Captured: "${args.signal}"\n${data.message || 'Task queued for processing'}`;
        }

        case 'lyco_get_queue': {
          const { data } = await client.get('/api/queue-preview', {
            params: { limit: args.count || 5 }
          });

          return this.formatQueue(data);
        }

        case 'lyco_weekly_review': {
          const { data } = await client.get('/api/weekly-review');
          return this.formatWeeklyReview(data);
        }

        case 'lyco_update_energy': {
          const { data } = await client.post('/api/energy', {
            level: args.level
          });

          const energyEmoji = {
            high: '🚀',
            medium: '⚡',
            low: '🔋'
          }[args.level];

          return `${energyEmoji} Energy updated to ${args.level}`;
        }

        case 'lyco_get_patterns': {
          const { data } = await client.get('/api/patterns');
          return this.formatPatterns(data);
        }

        case 'lyco_status': {
          const { data } = await client.get('/api/status');
          const health = await client.get('/api/health');

          return this.formatStatus(data, health.data);
        }

        default:
          throw new Error(`Unknown tool: ${toolName}`);
      }
    } catch (error) {
      // Handle specific error cases
      if (error.response) {
        const status = error.response.status;
        const message = error.response.data?.error || error.message;

        if (status === 404) {
          return `Task not found. It may have been deleted or completed.`;
        } else if (status === 500) {
          return `Lyco service error. Please try again or check system status.`;
        } else {
          return `Error: ${message}`;
        }
      } else if (error.code === 'ECONNREFUSED') {
        return `Cannot connect to Lyco service. Please ensure it's running.`;
      } else {
        throw error;
      }
    }
  }

  formatTask(task) {
    const parts = [];

    if (task.content) {
      parts.push(`**Task:** ${task.content}`);
    }

    if (task.next_action) {
      parts.push(`**Next Action:** ${task.next_action}`);
    }

    if (task.time_estimate) {
      parts.push(`**Time:** ${task.time_estimate} minutes`);
    }

    if (task.energy_level) {
      const emoji = {
        high: '🚀',
        medium: '⚡',
        low: '🔋'
      }[task.energy_level];
      parts.push(`**Energy:** ${emoji} ${task.energy_level}`);
    }

    if (task.deadline) {
      const deadline = new Date(task.deadline);
      const now = new Date();
      const hoursUntil = Math.round((deadline - now) / (1000 * 60 * 60));

      if (hoursUntil < 24) {
        parts.push(`**⚠️ Deadline:** ${hoursUntil} hours`);
      } else {
        const daysUntil = Math.round(hoursUntil / 24);
        parts.push(`**Deadline:** ${daysUntil} days`);
      }
    }

    if (task.context_required && task.context_required.length > 0) {
      parts.push(`**Context:** ${task.context_required.join(', ')}`);
    }

    parts.push(`**ID:** ${task.id}`);

    return parts.join('\n');
  }

  formatQueue(queue) {
    if (!queue || queue.length === 0) {
      return "Queue is empty! 🎉";
    }

    const items = queue.map((task, index) => {
      const emoji = index === 0 ? '▶️' : `${index + 1}.`;
      const energy = {
        high: '🚀',
        medium: '⚡',
        low: '🔋'
      }[task.energy_level] || '';

      return `${emoji} ${task.content} ${energy} (${task.time_estimate || '?'}min)`;
    });

    return `**Upcoming Tasks:**\n${items.join('\n')}`;
  }

  formatRoundsSession(data) {
    if (!data.tasks || data.tasks.length === 0) {
      return "No tasks available for rounds session.";
    }

    return `**Rounds Session Started!** ⚡\n` +
           `Type: ${data.type || 'quick'}\n` +
           `Tasks to process: ${data.tasks.length}\n\n` +
           `First task:\n${this.formatTask(data.tasks[0])}\n\n` +
           `Respond with: yes (do it), no (skip), or later (postpone)`;
  }

  formatWeeklyReview(data) {
    const parts = ['**Weekly Review** 📊\n'];

    if (data.completed_count) {
      parts.push(`✅ Completed: ${data.completed_count} tasks`);
    }

    if (data.patterns && data.patterns.length > 0) {
      parts.push('\n**Patterns Noticed:**');
      data.patterns.forEach(p => parts.push(`• ${p}`));
    }

    if (data.insights && data.insights.length > 0) {
      parts.push('\n**Insights:**');
      data.insights.forEach(i => parts.push(`• ${i}`));
    }

    if (data.recommendations && data.recommendations.length > 0) {
      parts.push('\n**Recommendations:**');
      data.recommendations.forEach(r => parts.push(`• ${r}`));
    }

    return parts.join('\n');
  }

  formatPatterns(data) {
    if (!data || data.length === 0) {
      return "No patterns detected yet. Keep using Lyco to build insights!";
    }

    const parts = ['**Learned Patterns** 🧠\n'];

    data.forEach(pattern => {
      parts.push(`• ${pattern.description}`);
      if (pattern.frequency) {
        parts.push(`  Frequency: ${pattern.frequency}`);
      }
    });

    return parts.join('\n');
  }

  formatStatus(status, health) {
    const parts = [`**Lyco Status** 🟢\n`];

    if (status.pending_count !== undefined) {
      parts.push(`📋 Pending tasks: ${status.pending_count}`);
    }

    if (status.current_energy) {
      const emoji = {
        high: '🚀',
        medium: '⚡',
        low: '🔋'
      }[status.current_energy];
      parts.push(`${emoji} Energy: ${status.current_energy}`);
    }

    if (status.current_time) {
      parts.push(`🕐 Time: ${status.current_time}`);
    }

    if (health?.components?.cache) {
      const cache = health.components.cache;
      parts.push(`\n**Cache Performance:**`);
      parts.push(`• Hit rate: ${cache.hit_rate || 'N/A'}`);
      parts.push(`• Total requests: ${cache.total_requests || 0}`);
    }

    return parts.join('\n');
  }

  getSkipMessage(reason, data) {
    const messages = {
      'wrong-time': '⏰ Task rescheduled for better timing',
      'need-someone': '👥 Task delegated/marked for collaboration',
      'not-now': '📅 Task postponed to next suitable slot',
      'not-important': '🗑️ Task deprioritized',
      'low-energy': '🔋 Task moved to high-energy time slot'
    };

    return messages[reason] || '⏭️ Task skipped';
  }

  async run() {
    const transport = new StdioServerTransport();
    await this.server.connect(transport);
    console.error('Lyco MCP Server running on stdio');
  }
}

// Start the server
const server = new LycoMCPServer();
server.run().catch(console.error);
