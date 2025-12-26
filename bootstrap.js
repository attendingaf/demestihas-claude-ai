/**
 * EA-AI Bootstrap for Claude Desktop Integration
 * Version: 1.0.0
 * Target: <300ms initialization
 */

const fs = require("fs").promises;
const path = require("path");
const axios = require("axios");
const SmartMemoryClient = require("./smart-memory-client.js");

class EABootstrap {
  constructor() {
    this.startTime = Date.now();
    this.basePath = path.dirname(__filename);
    this.configPath =
      "/Users/menedemestihas/Library/Application Support/Claude/";
    this.agents = new Map();
    this.memory = new SmartMemoryClient(); // Use smart memory client
    this.cache = new Map();
    this.initialized = false;
    this.lycoBaseUrl = process.env.LYCO_URL || "http://localhost:8000";
    this.httpClient = axios.create({
      baseURL: this.lycoBaseUrl,
      timeout: 5000,
      headers: { "Content-Type": "application/json" },
    });
  }

  /**
   * Main initialization function - must complete in <300ms
   */
  async init(options = {}) {
    try {
      const config = {
        maxLatency: 300,
        fallbackEnabled: true,
        memoryShare: true,
        ...options,
      };

      // Phase 1: Core Identity (0-50ms)
      const identity = await this.initCore();

      // Phase 2: Parallel Load (50-250ms)
      const [memory, state, routing, cache, family] = await Promise.all([
        this.loadSmartMemory(),
        this.loadStateFile(),
        this.loadRoutingMatrix(),
        this.initializeCache(),
        this.loadFamilyContext(), // Lazy load
      ]);

      // Phase 3: Register Agents (250-280ms)
      await this.registerAgents();

      // Phase 4: Validation (280-300ms)
      const validation = await this.validateBootstrap();

      this.initialized = true;
      const bootstrapTime = Date.now() - this.startTime;

      if (bootstrapTime > config.maxLatency) {
        console.warn(`EA-AI bootstrap exceeded target: ${bootstrapTime}ms`);
      }

      return {
        status: "ready",
        bootstrapTime,
        identity,
        agents: Array.from(this.agents.keys()),
        validation,
      };
    } catch (error) {
      console.error("EA-AI Bootstrap failed:", error);
      if (options.fallbackEnabled) {
        return { status: "fallback", error: error.message };
      }
      throw error;
    }
  }

  /**
   * Initialize core identity
   */
  async initCore() {
    const identity = {
      role: "Demestihas Family AI Assistant",
      system: "EA-AI Enhanced Claude Desktop",
      version: "1.0.0",
      mode: "proactive_helpful",
      startup_time: Date.now(),
    };
    Object.freeze(identity);
    return identity;
  }

  /**
   * Load smart memory system
   */
  async loadSmartMemory() {
    try {
      const memoryPath = path.join(this.basePath, "smart-memory.md");
      const memoryContent = await fs.readFile(memoryPath, "utf8");

      // Parse memory patterns and store them
      const patterns = this.parseMemoryPatterns(memoryContent);
      const categories = [
        "family_context",
        "active_preferences",
        "session_state",
        "tool_history",
      ];

      await this.memory.set("patterns", patterns, {
        type: "configuration",
        importance: "high",
      });
      await this.memory.set("categories", categories, {
        type: "configuration",
        importance: "high",
      });

      const size = await this.memory.size();
      return { status: "loaded", items: size };
    } catch (error) {
      console.warn("Smart memory load failed, using defaults:", error.message);
      return { status: "default" };
    }
  }

  /**
   * Load state file for active session
   */
  async loadStateFile() {
    try {
      const statePath = path.join(this.basePath, "state.md");
      const stateContent = await fs.readFile(statePath, "utf8");

      await this.memory.set(
        "state",
        {
          content: stateContent,
          lastModified: Date.now(),
        },
        { type: "state", importance: "medium" },
      );

      return { status: "loaded" };
    } catch (error) {
      return { status: "default" };
    }
  }

  /**
   * Load routing matrix for tool selection
   */
  async loadRoutingMatrix() {
    try {
      const routingPath = path.join(this.basePath, "routing.md");
      const routingContent = await fs.readFile(routingPath, "utf8");

      // Define agent routing rules
      const routes = {
        pluma: ["email", "gmail", "draft", "reply", "inbox", "send"],
        huata: [
          "calendar",
          "schedule",
          "appointment",
          "meeting",
          "event",
          "availability",
        ],
        lyco: [
          "task",
          "todo",
          "priority",
          "deadline",
          "time",
          "when",
          "break down",
          "prioritize",
          "chunk",
          "focus",
          "energy",
          "next meeting",
          "free time",
          "timer",
          "reminder",
          "duration",
        ],
        kairos: [
          "linkedin",
          "networking",
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

      await this.memory.set("routing", routes, {
        type: "configuration",
        importance: "high",
      });
      return { status: "loaded", routes: Object.keys(routes).length };
    } catch (error) {
      return { status: "default" };
    }
  }

  /**
   * Initialize 3-tier cache system
   */
  async initializeCache() {
    // L1: Hot cache (in-memory)
    this.cache.set("L1", new Map());

    // L2: Warm cache (recent patterns)
    this.cache.set("L2", new Map());

    // L3: Cold cache (disk-based)
    this.cache.set("L3", new Map());

    // Preload common patterns
    setTimeout(() => this.warmCache(), 10);

    return { status: "initialized", tiers: 3 };
  }

  /**
   * Load family context (lazy)
   */
  async loadFamilyContext() {
    // Defer actual loading
    setTimeout(async () => {
      try {
        const familyPath = path.join(this.basePath, "family.md");
        const familyContent = await fs.readFile(familyPath, "utf8");
        await this.memory.set("family", familyContent, {
          type: "context",
          importance: "medium",
        });
      } catch (error) {
        // Non-critical, continue without family context
      }
    }, 100);

    return { status: "deferred" };
  }

  /**
   * Register specialized agents
   */
  async registerAgents() {
    const agentConfigs = [
      { name: "pluma", type: "email", priority: 1 },
      { name: "huata", type: "calendar", priority: 1 },
      { name: "lyco", type: "task_time", priority: 2 },
      { name: "kairos", type: "networking", priority: 2 },
    ];

    for (const config of agentConfigs) {
      this.agents.set(config.name, {
        ...config,
        status: "ready",
        handler: this.createAgentHandler(config.name),
      });
    }
  }

  /**
   * Create agent handler function
   */
  createAgentHandler(agentName) {
    return async (params) => {
      const startTime = Date.now();

      try {
        // Check cache first
        const cacheKey = `${agentName}:${JSON.stringify(params)}`;
        const cached = this.checkCache(cacheKey);
        if (cached) return cached;

        // Route to appropriate handler
        let result;
        switch (agentName) {
          case "pluma":
            result = await this.handleEmailOperation(params);
            break;
          case "huata":
            result = await this.handleCalendarOperation(params);
            break;
          case "lyco":
            result = await this.handleTaskOperation(params);
            break;
          case "kairos":
            result = await this.handleTimeOperation(params);
            break;
          default:
            throw new Error(`Unknown agent: ${agentName}`);
        }

        // Update cache
        this.updateCache(cacheKey, result);

        const latency = Date.now() - startTime;
        return { ...result, latency };
      } catch (error) {
        console.error(`Agent ${agentName} error:`, error);
        throw error;
      }
    };
  }

  /**
   * Route tool calls to appropriate agents
   */
  async routeToAgent(toolName, params) {
    const routing = (await this.memory.get("routing")) || {};

    // Find matching agent
    for (const [agent, keywords] of Object.entries(routing)) {
      if (
        keywords.some((keyword) => toolName.toLowerCase().includes(keyword))
      ) {
        const agentConfig = this.agents.get(agent);
        if (agentConfig && agentConfig.status === "ready") {
          return await agentConfig.handler(params);
        }
      }
    }

    // No matching agent found
    return null;
  }

  /**
   * Email operations handler (Pluma)
   */
  async handleEmailOperation(params) {
    // Integration with existing Pluma MCP server
    const plumaPath =
      "/Users/menedemestihas/Projects/demestihas-ai/pluma-mcp-server/src/index.js";

    return {
      agent: "pluma",
      operation: params.operation || "fetch",
      status: "delegated",
      path: plumaPath,
    };
  }

  /**
   * Calendar operations handler (Huata)
   */
  async handleCalendarOperation(params) {
    // 6-calendar conflict resolution
    const calendars = [
      "menelaos4@gmail.com",
      "mene@beltlineconsulting.co",
      "7dia35946hir6rbq10stda8hk4@group.calendar.google.com", // LyS Familia
      "e46i6ac3ipii8b7iugsqfeh2j8@group.calendar.google.com", // Limon y Sal
      "c4djl5q698b556jqliablah9uk@group.calendar.google.com", // Cindy
      "up5jrbrsng5le7qmu0uhi6pedo@group.calendar.google.com", // Au Pair
    ];

    return {
      agent: "huata",
      operation: "check_conflicts",
      calendars,
      status: "ready",
    };
  }

  /**
   * Task & Time Management handler (Lyco)
   * Handles ALL task breakdown, prioritization, time management, and scheduling
   */
  async handleTaskOperation(params) {
    try {
      // Handle different Lyco operations via HTTP
      switch (params.operation) {
        case "get_next_task":
          const taskResponse = await this.httpClient.get("/api/next-task");
          return {
            agent: "lyco",
            operation: "get_next_task",
            data: taskResponse.data,
            status: "success",
          };

        case "complete_task":
          const completeResponse = await this.httpClient.post(
            `/api/tasks/${params.task_id}/complete`,
          );
          return {
            agent: "lyco",
            operation: "complete_task",
            data: completeResponse.data,
            status: "success",
          };

        case "skip_task":
          const skipResponse = await this.httpClient.post(
            `/api/tasks/${params.task_id}/skip`,
            { reason: params.reason },
          );
          return {
            agent: "lyco",
            operation: "skip_task",
            data: skipResponse.data,
            status: "success",
          };

        case "start_rounds":
          const roundsResponse = await this.httpClient.post(
            "/api/rounds/start",
            {
              type: params.rounds_type || "morning",
              energy_level: params.energy_level,
            },
          );
          return {
            agent: "lyco",
            operation: "start_rounds",
            data: roundsResponse.data,
            status: "success",
          };

        case "rounds_decision":
          const decisionResponse = await this.httpClient.post(
            `/api/rounds/task/${params.task_id}/decision`,
            { decision: params.decision },
          );
          return {
            agent: "lyco",
            operation: "rounds_decision",
            data: decisionResponse.data,
            status: "success",
          };

        case "get_queue_preview":
          const queueResponse = await this.httpClient.get("/api/queue-preview");
          return {
            agent: "lyco",
            operation: "get_queue_preview",
            data: queueResponse.data,
            status: "success",
          };

        case "get_status":
          const statusResponse = await this.httpClient.get("/api/status");
          return {
            agent: "lyco",
            operation: "get_status",
            data: statusResponse.data,
            status: "success",
          };

        case "signal_capture":
          const signalResponse = await this.httpClient.post("/api/signals", {
            signal: params.signal,
            context: params.context,
          });
          return {
            agent: "lyco",
            operation: "signal_capture",
            data: signalResponse.data,
            status: "success",
          };

        case "process_signals":
          const processResponse = await this.httpClient.post("/api/process");
          return {
            agent: "lyco",
            operation: "process_signals",
            data: processResponse.data,
            status: "success",
          };

        case "get_patterns":
          const patternsResponse = await this.httpClient.get("/api/patterns");
          return {
            agent: "lyco",
            operation: "get_patterns",
            data: patternsResponse.data,
            status: "success",
          };

        case "weekly_review":
          const reviewResponse =
            await this.httpClient.get("/api/weekly-review");
          return {
            agent: "lyco",
            operation: "weekly_review",
            data: reviewResponse.data,
            status: "success",
          };

        case "update_energy":
          const energyResponse = await this.httpClient.post("/api/energy", {
            level: params.energy_level,
          });
          return {
            agent: "lyco",
            operation: "update_energy",
            data: energyResponse.data,
            status: "success",
          };

        case "get_delegation_signals":
          const delegationResponse = await this.httpClient.get(
            "/api/delegation-signals",
          );
          return {
            agent: "lyco",
            operation: "get_delegation_signals",
            data: delegationResponse.data,
            status: "success",
          };

        case "rounds_summary":
          const summaryResponse = await this.httpClient.get(
            "/api/rounds/summary",
          );
          return {
            agent: "lyco",
            operation: "rounds_summary",
            data: summaryResponse.data,
            status: "success",
          };

        default:
          // Fallback to metadata-only response for unknown operations
          return {
            agent: "lyco",
            operation: params.operation || "manage_task",
            capabilities: [
              "task_breakdown",
              "prioritization",
              "time_management",
            ],
            adhd_optimized: true,
            chunk_size: "15min",
            status: "ready",
          };
      }
    } catch (error) {
      console.error("Lyco HTTP operation failed:", error.message);
      return {
        agent: "lyco",
        operation: params.operation,
        error: error.message,
        status: "error",
      };
    }
  }

  /**
   * Networking & Professional Development handler (Kairos)
   * Professional coach, networking assistant, and administrative support
   */
  async handleTimeOperation(params) {
    return {
      agent: "kairos",
      operation: params.operation || "professional_support",
      capabilities: [
        "linkedin",
        "networking",
        "career_coaching",
        "admin_tasks",
        "relationship_management",
        "meeting_prep",
        "crm",
      ],
      status: "ready",
    };
  }

  /**
   * Cache operations
   */
  checkCache(key) {
    // Check L1 (hot)
    const l1 = this.cache.get("L1");
    if (l1.has(key)) return l1.get(key);

    // Check L2 (warm)
    const l2 = this.cache.get("L2");
    if (l2.has(key)) {
      // Promote to L1
      const value = l2.get(key);
      l1.set(key, value);
      return value;
    }

    // Check L3 (cold)
    const l3 = this.cache.get("L3");
    if (l3.has(key)) {
      // Promote to L2
      const value = l3.get(key);
      l2.set(key, value);
      return value;
    }

    return null;
  }

  updateCache(key, value) {
    const l1 = this.cache.get("L1");
    l1.set(key, value);

    // Manage cache size (simple LRU)
    if (l1.size > 100) {
      const firstKey = l1.keys().next().value;
      l1.delete(firstKey);
    }
  }

  async warmCache() {
    // Preload common patterns
    const commonPatterns = [
      "check_calendar",
      "fetch_emails",
      "list_tasks",
      "family_schedule",
    ];

    for (const pattern of commonPatterns) {
      this.cache.get("L2").set(pattern, { preloaded: true });
    }
  }

  /**
   * Parse memory patterns from markdown
   */
  parseMemoryPatterns(content) {
    const patterns = [];
    const lines = content.split("\n");

    for (const line of lines) {
      if (line.startsWith("- ") || line.startsWith("* ")) {
        patterns.push(line.substring(2).trim());
      }
    }

    return patterns;
  }

  /**
   * Validate bootstrap completion
   */
  async validateBootstrap() {
    const memorySize = await this.memory.size();
    const hasRouting = (await this.memory.get("routing")) !== null;

    const checks = {
      memory_loaded: memorySize > 0,
      agents_registered: this.agents.size === 4,
      cache_initialized: this.cache.size === 3,
      routing_ready: hasRouting,
    };

    const allPassed = Object.values(checks).every(Boolean);

    return {
      passed: allPassed,
      checks,
      bootstrapTime: Date.now() - this.startTime,
    };
  }

  /**
   * Update memory with new patterns
   */
  async updateMemory(updates) {
    for (const [key, value] of Object.entries(updates)) {
      await this.memory.set(key, value, {
        type: "update",
        importance: "medium",
      });
    }

    // Persist to disk if needed
    if (updates.persist) {
      await this.persistMemory();
    }
  }

  /**
   * Persist memory to disk
   */
  async persistMemory() {
    // The smart memory client handles persistence automatically
    // Just call persist to ensure everything is saved
    const result = await this.memory.persist();
    console.log("EA-AI memory persisted:", result);
    return result;
  }

  /**
   * Shutdown and cleanup
   */
  async shutdown() {
    await this.persistMemory();
    this.agents.clear();
    this.cache.clear();
    this.initialized = false;
  }
}

// Export for Claude Desktop integration
module.exports = new EABootstrap();
