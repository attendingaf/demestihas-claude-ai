#!/usr/bin/env node

import { Server } from "@modelcontextprotocol/sdk/server/index.js";
import { StdioServerTransport } from "@modelcontextprotocol/sdk/server/stdio.js";
import {
    CallToolRequestSchema,
    ListToolsRequestSchema,
    ErrorCode,
    McpError
} from "@modelcontextprotocol/sdk/types.js";
import { z } from "zod";
import { supabase, TABLES } from "./db.js";

const VALID_QUADRANTS = ['do_now', 'schedule', 'delegate', 'defer', 'inbox'] as const;
const VALID_STATUSES = ['active', 'completed', 'archived'] as const;

class VantageServer {
    private server: Server;

    constructor() {
        this.server = new Server(
            {
                name: "vantage-service",
                version: "1.0.0",
            },
            {
                capabilities: {
                    tools: {},
                },
            }
        );

        this.setupToolHandlers();

        // Error handling
        this.server.onerror = (error) => console.error('[MCP Error]', error);
        process.on('SIGINT', async () => {
            await this.server.close();
            process.exit(0);
        });
    }

    private setupToolHandlers() {
        this.server.setRequestHandler(ListToolsRequestSchema, async () => ({
            tools: [
                {
                    name: "vantage_get_dashboard",
                    description: "Get the Vantage Dashboard. Returns all active tasks grouped by Eisenhower Quadrant.",
                    inputSchema: {
                        type: "object",
                        properties: {},
                    },
                },
                {
                    name: "vantage_add_task",
                    description: "Add a new task to the Vantage system.",
                    inputSchema: {
                        type: "object",
                        properties: {
                            title: { type: "string", description: "The task title" },
                            quadrant: {
                                type: "string",
                                enum: VALID_QUADRANTS,
                                description: "The Eisenhower quadrant"
                            },
                            context: { type: "string", description: "The 'Why'. Context on importance/urgency." },
                            deadline: { type: "string", description: "ISO date string" },
                            owner: { type: "string", description: "Owner of the task (default: Mene)" },
                        },
                        required: ["title", "quadrant", "context"],
                    },
                },
                {
                    name: "vantage_update_task",
                    description: "Update a task's status or quadrant. REASON IS MANDATORY to preserve history.",
                    inputSchema: {
                        type: "object",
                        properties: {
                            id: { type: "string", description: "Task UUID" },
                            reason: { type: "string", description: "The MANDATORY reason for this change." },
                            quadrant: { type: "string", enum: VALID_QUADRANTS },
                            status: { type: "string", enum: VALID_STATUSES },
                            context: { type: "string", description: "Update the context/description" },
                        },
                        required: ["id", "reason"],
                    },
                },
                {
                    name: "vantage_get_history",
                    description: "Get the full changelog history for a specific task to understand its lifecycle.",
                    inputSchema: {
                        type: "object",
                        properties: {
                            id: { type: "string", description: "Task UUID" },
                        },
                        required: ["id"],
                    },
                },
            ],
        }));

        this.server.setRequestHandler(CallToolRequestSchema, async (request) => {
            const { name, arguments: args } = request.params;

            try {
                switch (name) {
                    case "vantage_get_dashboard":
                        return await this.handleGetDashboard();
                    case "vantage_add_task":
                        return await this.handleAddTask(args);
                    case "vantage_update_task":
                        return await this.handleUpdateTask(args);
                    case "vantage_get_history":
                        return await this.handleGetHistory(args);
                    default:
                        throw new McpError(ErrorCode.MethodNotFound, `Unknown tool: ${name}`);
                }
            } catch (error: any) {
                console.error("Error executing tool:", error);
                return {
                    content: [
                        {
                            type: "text",
                            text: `Error: ${error.message}`,
                        },
                    ],
                    isError: true,
                };
            }
        });
    }

    private async handleGetDashboard() {
        const { data: tasks, error } = await supabase
            .from(TABLES.TASKS)
            .select('*')
            .eq('status', 'active')
            .order('created_at', { ascending: false });

        if (error) throw new Error(`Supabase error: ${error.message}`);

        // Group by quadrant
        const dashboard: Record<string, any[]> = {
            do_now: [],
            schedule: [],
            delegate: [],
            defer: [],
            inbox: []
        };

        tasks?.forEach(task => {
            if (dashboard[task.quadrant]) {
                dashboard[task.quadrant].push(task);
            } else {
                dashboard.inbox.push(task);
            }
        });

        const markdown = `
# 🦅 Vantage Dashboard

## 🔥 Do Now (Urgent & Important)
${this.formatTaskList(dashboard.do_now)}

## 🗓 Schedule (Important, Not Urgent)
${this.formatTaskList(dashboard.schedule)}

## 🤝 Delegate (Urgent, Not Important)
${this.formatTaskList(dashboard.delegate)}

## ⏳ Defer (Neither)
${this.formatTaskList(dashboard.defer)}

## 📥 Inbox / Unsorted
${this.formatTaskList(dashboard.inbox)}
`;

        return {
            content: [{ type: "text", text: markdown }]
        };
    }

    private formatTaskList(tasks: any[]): string {
        if (!tasks || tasks.length === 0) return "_No tasks._";
        return tasks.map(t => `- **[${t.title}]** (ID: \`${t.id}\`)\n  - *Why:* ${t.context || 'No context'}\n  - *Owner:* ${t.owner}`).join('\n');
    }

    private async handleAddTask(args: any) {
        const { title, quadrant, context, deadline, owner = 'Mene' } = args;

        const { data, error } = await supabase.from(TABLES.TASKS).insert({
            title,
            quadrant,
            context,
            deadline,
            owner,
            status: 'active'
        }).select().single();

        if (error) throw new Error(error.message);

        // Log creation
        await this.logChange(data.id, 'creation', null, data, "Initial creation", "Claude");

        return {
            content: [{ type: "text", text: `✅ Task Created: **${title}** in ${quadrant}. (ID: ${data.id})` }]
        };
    }

    private async handleUpdateTask(args: any) {
        const { id, reason, ...updates } = args;

        // 1. Get current state
        const { data: current, error: fetchError } = await supabase
            .from(TABLES.TASKS)
            .select('*')
            .eq('id', id)
            .single();

        if (fetchError || !current) throw new Error("Task not found");

        // 2. Update
        const { data: updated, error: updateError } = await supabase
            .from(TABLES.TASKS)
            .update(updates)
            .eq('id', id)
            .select()
            .single();

        if (updateError) throw new Error(updateError.message);

        // 3. Log change
        await this.logChange(id, 'update', current, updated, reason, "Claude");

        return {
            content: [{ type: "text", text: `✅ Task Updated: **${updated.title}**. Reason logged: "${reason}"` }]
        };
    }

    private async handleGetHistory(args: any) {
        const { id } = args;

        const { data: logs, error } = await supabase
            .from(TABLES.CHANGELOG)
            .select('*')
            .eq('task_id', id)
            .order('changed_at', { ascending: false });

        if (error) throw new Error(error.message);

        const history = logs?.map(log => {
            return `- **${new Date(log.changed_at).toLocaleString()}** (${log.agent_id}): ${log.change_type}\n  - Reason: "${log.reason}"\n  - Changes: ${this.diff(log.previous_value, log.new_value)}`;
        }).join('\n\n');

        return {
            content: [{ type: "text", text: `# 📜 History for Task ${id}\n\n${history}` }]
        };
    }

    private async logChange(taskId: string, type: string, prev: any, curr: any, reason: string, agent: string) {
        await supabase.from(TABLES.CHANGELOG).insert({
            task_id: taskId,
            change_type: type,
            previous_value: prev,
            new_value: curr,
            reason: reason,
            agent_id: agent
        });
    }

    private diff(prev: any, curr: any): string {
        if (!prev) return "Created";
        const changes: string[] = [];
        for (const key in curr) {
            if (curr[key] !== prev[key]) {
                changes.push(`${key}: ${prev[key]} -> ${curr[key]}`);
            }
        }
        return changes.join(', ');
    }

    async run() {
        const transport = new StdioServerTransport();
        await this.server.connect(transport);
        console.error("🦅 Vantage Service (MCP) running on stdio");
    }
}

const server = new VantageServer();
server.run().catch(console.error);
