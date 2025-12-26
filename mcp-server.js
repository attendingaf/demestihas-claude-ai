#!/usr/bin/env node

/**
 * EA-AI MCP Server for Claude Desktop
 * This integrates the EA-AI bootstrap system with Claude Desktop
 * through the Model Context Protocol
 */

const { Server } = require("@modelcontextprotocol/sdk/server/index.js");
const {
  StdioServerTransport,
} = require("@modelcontextprotocol/sdk/server/stdio.js");
const {
  CallToolRequestSchema,
  ErrorCode,
  ListToolsRequestSchema,
  McpError,
} = require("@modelcontextprotocol/sdk/types.js");
const EABootstrap = require("./bootstrap.js");

class EAAIServer {
  constructor() {
    this.server = new Server(
      {
        name: "ea-ai-system",
        version: "1.0.0",
      },
      {
        capabilities: {
          tools: {},
        },
      },
    );

    this.setupToolHandlers();
    this.initializeBootstrap();
  }

  async initializeBootstrap() {
    console.error("Initializing EA-AI Bootstrap...");

    try {
      const result = await EABootstrap.init({
        maxLatency: 300,
        fallbackEnabled: true,
        memoryShare: true,
      });

      console.error(`EA-AI Bootstrap completed in ${result.bootstrapTime}ms`);
      console.error(`Agents ready: ${result.agents.join(", ")}`);
    } catch (error) {
      console.error("EA-AI Bootstrap failed:", error);
    }
  }

  setupToolHandlers() {
    // List available tools
    this.server.setRequestHandler(ListToolsRequestSchema, async () => ({
      tools: [
        {
          name: "ea_ai_route",
          description: "Route requests through EA-AI specialized agents",
          inputSchema: {
            type: "object",
            properties: {
              agent: {
                type: "string",
                enum: ["pluma", "huata", "lyco", "kairos", "auto"],
                description: "Target agent or auto for automatic routing",
              },
              operation: {
                type: "string",
                description: "Operation to perform",
              },
              params: {
                type: "object",
                description: "Parameters for the operation",
              },
            },
            required: ["operation"],
          },
        },
        {
          name: "ea_ai_memory",
          description: "Access EA-AI smart memory system",
          inputSchema: {
            type: "object",
            properties: {
              action: {
                type: "string",
                enum: ["get", "set", "search", "persist"],
                description: "Memory action",
              },
              category: {
                type: "string",
                description: "Memory category",
              },
              key: {
                type: "string",
                description: "Memory key",
              },
              value: {
                type: "any",
                description: "Value for set operations",
              },
            },
            required: ["action"],
          },
        },
        {
          name: "ea_ai_family",
          description: "Access family context and personalization",
          inputSchema: {
            type: "object",
            properties: {
              member: {
                type: "string",
                enum: ["mene", "cindy", "elena", "aris", "eleni", "auto"],
                description: "Family member or auto-detect",
              },
              context: {
                type: "string",
                description: "Context type needed",
              },
            },
            required: ["context"],
          },
        },
        {
          name: "ea_ai_calendar_check",
          description: "Check all 6 calendars for conflicts and free time",
          inputSchema: {
            type: "object",
            properties: {
              action: {
                type: "string",
                enum: ["check_conflicts", "find_free_time", "next_event"],
                description: "Calendar action",
              },
              timeRange: {
                type: "object",
                properties: {
                  start: { type: "string" },
                  end: { type: "string" },
                },
              },
            },
            required: ["action"],
          },
        },
        {
          name: "ea_ai_task_adhd",
          description: "ADHD-optimized task management",
          inputSchema: {
            type: "object",
            properties: {
              task: {
                type: "string",
                description: "Task description",
              },
              action: {
                type: "string",
                enum: [
                  "break_down",
                  "prioritize",
                  "time_block",
                  "energy_match",
                ],
                description: "Task management action",
              },
              duration: {
                type: "number",
                description: "Estimated duration in minutes",
              },
            },
            required: ["task", "action"],
          },
        },
      ],
    }));

    // Handle tool calls
    this.server.setRequestHandler(CallToolRequestSchema, async (request) => {
      const { name, arguments: args } = request.params;

      try {
        switch (name) {
          case "ea_ai_route":
            return await this.handleRoute(args);

          case "ea_ai_memory":
            return await this.handleMemory(args);

          case "ea_ai_family":
            return await this.handleFamily(args);

          case "ea_ai_calendar_check":
            return await this.handleCalendarCheck(args);

          case "ea_ai_task_adhd":
            return await this.handleTaskADHD(args);

          default:
            throw new McpError(
              ErrorCode.MethodNotFound,
              `Unknown tool: ${name}`,
            );
        }
      } catch (error) {
        if (error instanceof McpError) throw error;

        throw new McpError(
          ErrorCode.InternalError,
          `Tool execution failed: ${error.message}`,
        );
      }
    });
  }

  async handleRoute(args) {
    const { agent, operation, params = {} } = args;

    // Auto-detect agent if not specified
    const targetAgent = agent === "auto" ? this.detectAgent(operation) : agent;

    // For Lyco, include operation details
    const routeParams =
      targetAgent === "lyco"
        ? { operation, ...params }
        : { operation, ...params };

    const result = await EABootstrap.routeToAgent(targetAgent, routeParams);

    return {
      content: [
        {
          type: "text",
          text: JSON.stringify(
            {
              agent: targetAgent,
              result,
              latency: result?.latency || "N/A",
            },
            null,
            2,
          ),
        },
      ],
    };
  }

  async handleMemory(args) {
    const { action, category, key, value } = args;

    let result;
    switch (action) {
      case "get":
        result = EABootstrap.memory.get(key);
        break;

      case "set":
        EABootstrap.memory.set(key, value);
        result = { success: true };
        break;

      case "search":
        result = Array.from(EABootstrap.memory.entries()).filter(
          ([k, v]) => k.includes(key) || JSON.stringify(v).includes(key),
        );
        break;

      case "persist":
        await EABootstrap.persistMemory();
        result = { persisted: true, items: EABootstrap.memory.size };
        break;
    }

    return {
      content: [
        {
          type: "text",
          text: JSON.stringify(result, null, 2),
        },
      ],
    };
  }

  async handleFamily(args) {
    const { member, context } = args;

    // Get family context from memory
    const familyData = EABootstrap.memory.get("family") || {};

    const memberContext =
      member === "auto" ? this.detectFamilyMember(context) : member;

    return {
      content: [
        {
          type: "text",
          text: JSON.stringify(
            {
              member: memberContext,
              context: context,
              personalizations: this.getFamilyPersonalizations(memberContext),
            },
            null,
            2,
          ),
        },
      ],
    };
  }

  async handleCalendarCheck(args) {
    const { action, timeRange } = args;

    const calendars = [
      "menelaos4@gmail.com",
      "mene@beltlineconsulting.co",
      "7dia35946hir6rbq10stda8hk4@group.calendar.google.com",
      "e46i6ac3ipii8b7iugsqfeh2j8@group.calendar.google.com",
      "c4djl5q698b556jqliablah9uk@group.calendar.google.com",
      "up5jrbrsng5le7qmu0uhi6pedo@group.calendar.google.com",
    ];

    return {
      content: [
        {
          type: "text",
          text: JSON.stringify(
            {
              action,
              calendars,
              timeRange,
              note: "Use list_gcal_events tool with these calendar IDs for actual data",
            },
            null,
            2,
          ),
        },
      ],
    };
  }

  async handleTaskADHD(args) {
    const { task, action, duration } = args;

    let result;
    switch (action) {
      case "break_down":
        result = this.breakDownTask(task, duration);
        break;

      case "prioritize":
        result = this.prioritizeTask(task);
        break;

      case "time_block":
        result = this.timeBlockTask(task, duration);
        break;

      case "energy_match":
        result = this.matchTaskToEnergy(task);
        break;
    }

    return {
      content: [
        {
          type: "text",
          text: JSON.stringify(result, null, 2),
        },
      ],
    };
  }

  // Helper methods
  detectAgent(operation) {
    const opLower = operation.toLowerCase();

    // Check for specific multi-word phrases first (higher priority)
    if (opLower.includes("next meeting") || opLower.includes("free time")) {
      return "lyco";
    }

    if (
      opLower.includes("linkedin") ||
      opLower.includes("professional introduction") ||
      opLower.includes("networking") ||
      opLower.includes("administrative")
    ) {
      return "kairos";
    }

    // Then check single keywords in priority order
    const keywords = {
      pluma: ["email", "gmail", "inbox", "send"],
      huata: ["calendar", "appointment", "event", "availability"],
      lyco: [
        "task",
        "todo",
        "priority",
        "deadline",
        "when",
        "break down",
        "prioritize",
        "chunk",
        "focus",
        "energy",
        "timer",
        "reminder",
        "duration",
        "time",
      ],
      kairos: [
        "professional",
        "introduction",
        "admin",
        "contact",
        "relationship",
        "career",
        "coach",
        "crm",
        "administrative",
      ],
    };

    // Special handling for ambiguous keywords
    if (opLower.includes("schedule")) {
      // If it's about scheduling time for work, it's Lyco
      if (
        opLower.includes("time") ||
        opLower.includes("work") ||
        opLower.includes("task")
      ) {
        return "lyco";
      }
      // If it's about scheduling meetings/events, it's Huata
      if (
        opLower.includes("meeting") ||
        opLower.includes("event") ||
        opLower.includes("appointment")
      ) {
        return "huata";
      }
      // Default schedule to Lyco (time management)
      return "lyco";
    }

    if (opLower.includes("meeting")) {
      // "next meeting" queries go to Lyco (time awareness)
      if (opLower.includes("next") || opLower.includes("when")) {
        return "lyco";
      }
      // Scheduling meetings goes to Huata
      return "huata";
    }

    // Standard keyword matching
    for (const [agent, words] of Object.entries(keywords)) {
      if (words.some((word) => opLower.includes(word))) {
        return agent;
      }
    }

    return "lyco"; // Default to task manager
  }

  detectFamilyMember(context) {
    // Simple detection based on context
    if (context.includes("medical") || context.includes("executive"))
      return "mene";
    if (context.includes("kids") || context.includes("school")) return "cindy";
    return "mene"; // Default
  }

  getFamilyPersonalizations(member) {
    const personalizations = {
      mene: {
        role: "Physician Executive",
        preferences: "Direct, execution-focused",
        adhd: "Hyperactive type",
        enneagram: "Eight",
      },
      cindy: {
        role: "Family Coordinator",
        preferences: "Detailed, planning-focused",
        adhd: "Inattentive type",
        enneagram: "Six",
      },
    };

    return personalizations[member] || {};
  }

  breakDownTask(task, duration = 60) {
    const chunks = Math.ceil(duration / 15);
    const subtasks = [];

    for (let i = 0; i < chunks; i++) {
      subtasks.push({
        chunk: i + 1,
        duration: Math.min(15, duration - i * 15),
        description: `${task} - Part ${i + 1}`,
      });
    }

    return {
      task,
      totalDuration: duration,
      chunks: subtasks,
      adhd_note: "Broken into 15-minute focus blocks",
    };
  }

  prioritizeTask(task) {
    // Simple prioritization logic
    const urgentKeywords = ["urgent", "asap", "emergency", "critical"];
    const importantKeywords = ["important", "key", "vital", "essential"];

    const isUrgent = urgentKeywords.some((word) =>
      task.toLowerCase().includes(word),
    );
    const isImportant = importantKeywords.some((word) =>
      task.toLowerCase().includes(word),
    );

    return {
      task,
      quadrant:
        isUrgent && isImportant
          ? "Q1: Do First"
          : isImportant
            ? "Q2: Schedule"
            : isUrgent
              ? "Q3: Delegate"
              : "Q4: Delete/Defer",
      priority:
        isUrgent && isImportant
          ? "Critical"
          : isImportant
            ? "High"
            : isUrgent
              ? "Medium"
              : "Low",
    };
  }

  timeBlockTask(task, duration = 30) {
    const now = new Date();
    const blocks = [];

    // Find next available 15-minute blocks
    for (let i = 0; i < Math.ceil(duration / 15); i++) {
      const blockStart = new Date(now.getTime() + i * 15 * 60000);
      const blockEnd = new Date(blockStart.getTime() + 15 * 60000);

      blocks.push({
        start: blockStart.toISOString(),
        end: blockEnd.toISOString(),
        task: `${task} - Block ${i + 1}`,
      });
    }

    return {
      task,
      duration,
      blocks,
      strategy: "Pomodoro-style time blocking",
    };
  }

  matchTaskToEnergy(task) {
    const highEnergyTasks = ["creative", "strategic", "complex", "analysis"];
    const lowEnergyTasks = ["routine", "email", "review", "organize"];

    const requiresHighEnergy = highEnergyTasks.some((word) =>
      task.toLowerCase().includes(word),
    );

    return {
      task,
      energyLevel: requiresHighEnergy ? "High" : "Low",
      bestTime: requiresHighEnergy ? "Morning (9-11am)" : "Afternoon (2-4pm)",
      adhd_tip: requiresHighEnergy
        ? "Do this when medication is most effective"
        : "Good for low-focus periods",
    };
  }

  async run() {
    const transport = new StdioServerTransport();
    await this.server.connect(transport);
    console.error("EA-AI MCP Server running");
  }
}

// Start the server
const server = new EAAIServer();
server.run().catch(console.error);
