/**
 * EA-AI Containerized Subagent Server
 * HTTP bridge for EA-AI toolset functionality
 */

const express = require("express");
const bodyParser = require("body-parser");
const cors = require("cors");
const axios = require("axios");
const fs = require("fs").promises;
const path = require("path");
const winston = require("winston");

// Configure logging
const logger = winston.createLogger({
  level: "info",
  format: winston.format.json(),
  transports: [
    new winston.transports.File({
      filename: "/app/logs/error.log",
      level: "error",
    }),
    new winston.transports.File({ filename: "/app/logs/combined.log" }),
    new winston.transports.Console({ format: winston.format.simple() }),
  ],
});

// Initialize Express
const app = express();
app.use(cors());
app.use(bodyParser.json());
app.use(bodyParser.urlencoded({ extended: true }));

// In-memory state management
const state = {
  agents: new Map(),
  memory: new Map(),
  cache: new Map(),
  routing: new Map(),
  family: new Map(),
};

// Initialize agent routing matrix
const initializeRouting = () => {
  state.routing.set("pluma", [
    "email",
    "gmail",
    "draft",
    "reply",
    "inbox",
    "send",
  ]);
  state.routing.set("huata", [
    "calendar",
    "schedule",
    "appointment",
    "meeting",
    "event",
    "availability",
  ]);
  state.routing.set("lyco", [
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
  ]);
  state.routing.set("kairos", [
    "linkedin",
    "networking",
    "professional",
    "introduction",
    "admin",
    "contact",
    "relationship",
    "career",
  ]);
};

// Initialize family context
const initializeFamilyContext = () => {
  state.family.set("mene", {
    preferences: {
      morning_energy: "9-11am",
      adhd_chunks: 15,
      email_style: "warm_professional",
      decision_format: "trade_offs",
    },
  });
  state.family.set("cindy", {
    schedule: {
      work: "8am-3:30pm weekdays",
      routines: {
        morning: "6:30am prep",
        evening: "dinner 6:30pm, bedtime 8:30pm",
      },
    },
  });
};

// Agent registry
const registerAgents = () => {
  state.agents.set("pluma", { role: "Email Intelligence", status: "ready" });
  state.agents.set("huata", {
    role: "Calendar Orchestration",
    status: "ready",
  });
  state.agents.set("lyco", { role: "Task & Time Management", status: "ready" });
  state.agents.set("kairos", {
    role: "Networking & Professional Development",
    status: "ready",
  });
};

// API Routes

// Health check
app.get("/health", (req, res) => {
  res.json({
    service: "ea-ai-bridge",
    status: "healthy",
    agents: Array.from(state.agents.keys()),
    memory_size: state.memory.size,
    cache_size: state.cache.size,
    uptime: process.uptime(),
    dependencies: {
      lyco: process.env.LYCO_URL || "http://lyco-v2:8000",
      huata: process.env.HUATA_URL || "http://huata:8003",
      mcp_memory: process.env.MCP_MEMORY_URL || "http://mcp-memory:7777",
      redis: `${process.env.REDIS_HOST || "redis"}:${process.env.REDIS_PORT || 6379}`,
    },
  });
});

// Memory operations
app.post("/memory", async (req, res) => {
  try {
    const { operation, key, value, metadata } = req.body;

    switch (operation) {
      case "set":
        state.memory.set(key, { value, metadata, timestamp: Date.now() });
        res.json({ success: true, key });
        break;

      case "get":
        const item = state.memory.get(key);
        res.json({ success: true, data: item });
        break;

      case "search":
        const results = [];
        state.memory.forEach((item, k) => {
          if (
            k.includes(key) ||
            (item.value && item.value.toString().includes(key))
          ) {
            results.push({ key: k, ...item });
          }
        });
        res.json({ success: true, results });
        break;

      case "persist":
        // Save to disk for persistence
        const memoryData = Object.fromEntries(state.memory);
        await fs.writeFile(
          "/app/state/memory.json",
          JSON.stringify(memoryData, null, 2),
        );
        res.json({ success: true, persisted: state.memory.size });
        break;

      default:
        res.status(400).json({ error: "Invalid operation" });
    }
  } catch (error) {
    logger.error("Memory operation failed:", error);
    res.status(500).json({ error: error.message });
  }
});

// Agent routing
app.post("/route", (req, res) => {
  try {
    const { agent, query } = req.body;

    if (agent === "auto") {
      // Auto-route based on keywords
      let selectedAgent = null;
      let maxScore = 0;

      state.routing.forEach((keywords, agentName) => {
        const score = keywords.filter((kw) =>
          query.toLowerCase().includes(kw),
        ).length;
        if (score > maxScore) {
          maxScore = score;
          selectedAgent = agentName;
        }
      });

      if (selectedAgent) {
        res.json({
          success: true,
          agent: selectedAgent,
          confidence: maxScore / state.routing.get(selectedAgent).length,
        });
      } else {
        res.json({
          success: false,
          message: "No suitable agent found",
          suggestion: "lyco", // Default to Lyco for general tasks
        });
      }
    } else {
      // Direct routing
      if (state.agents.has(agent)) {
        res.json({
          success: true,
          agent,
          status: state.agents.get(agent).status,
        });
      } else {
        res.status(404).json({ error: "Agent not found" });
      }
    }
  } catch (error) {
    logger.error("Routing failed:", error);
    res.status(500).json({ error: error.message });
  }
});

// Family context
app.get("/family/:member", (req, res) => {
  try {
    const { member } = req.params;

    if (member === "auto" || member === "current") {
      // Return all family context
      const context = Object.fromEntries(state.family);
      res.json({ success: true, context });
    } else if (state.family.has(member)) {
      res.json({ success: true, data: state.family.get(member) });
    } else {
      res.status(404).json({ error: "Family member not found" });
    }
  } catch (error) {
    logger.error("Family context retrieval failed:", error);
    res.status(500).json({ error: error.message });
  }
});

// Calendar check proxy (connects to Huata)
app.post("/calendar/check", async (req, res) => {
  try {
    const { operation, params } = req.body;

    // Forward to Huata container if available
    const huataUrl =
      process.env.HUATA_URL || "http://huata-calendar-agent:8003";
    const response = await axios.post(
      `${huataUrl}/api/calendar/${operation}`,
      params,
    );

    res.json(response.data);
  } catch (error) {
    logger.error("Calendar check failed:", error);
    res.status(500).json({ error: "Calendar service unavailable" });
  }
});

// Calendar conflict detection endpoints
app.get("/calendar/conflicts", async (req, res) => {
  try {
    const huataUrl = process.env.HUATA_URL || "http://huata:8080";
    const { days = 7, start_date, end_date } = req.query;

    const params = new URLSearchParams();
    params.append("days", days);
    if (start_date) params.append("start_date", start_date);
    if (end_date) params.append("end_date", end_date);

    const response = await axios.get(
      `${huataUrl}/conflicts?${params.toString()}`,
    );

    res.json(response.data);
  } catch (error) {
    logger.error("Conflict detection failed:", error);
    res.status(500).json({ error: "Conflict detection service unavailable" });
  }
});

app.post("/calendar/conflicts/check", async (req, res) => {
  try {
    const huataUrl = process.env.HUATA_URL || "http://huata:8080";
    const response = await axios.post(`${huataUrl}/conflicts/check`, req.body);

    res.json(response.data);
  } catch (error) {
    logger.error("Conflict check failed:", error);
    res.status(500).json({ error: "Conflict check service unavailable" });
  }
});

app.get("/calendar/conflicts/free-slots", async (req, res) => {
  try {
    const huataUrl = process.env.HUATA_URL || "http://huata:8080";
    const {
      duration_minutes = 60,
      days = 7,
      start_hour = 9,
      end_hour = 17,
    } = req.query;

    const params = new URLSearchParams();
    params.append("duration_minutes", duration_minutes);
    params.append("days", days);
    params.append("start_hour", start_hour);
    params.append("end_hour", end_hour);

    const response = await axios.get(
      `${huataUrl}/conflicts/free-slots?${params.toString()}`,
    );

    res.json(response.data);
  } catch (error) {
    logger.error("Free slot search failed:", error);
    res.status(500).json({ error: "Free slot service unavailable" });
  }
});

// ADHD task management
app.post("/task/adhd", (req, res) => {
  try {
    const { operation, task } = req.body;

    switch (operation) {
      case "break_down":
        // Break task into 15-minute chunks
        const chunks = [];
        const words = task.split(" ");
        const chunkSize = Math.ceil(words.length / 3);

        for (let i = 0; i < 3; i++) {
          const chunk = words
            .slice(i * chunkSize, (i + 1) * chunkSize)
            .join(" ");
          if (chunk) {
            chunks.push({
              id: `chunk_${i + 1}`,
              duration: 15,
              description: chunk,
              energy: i === 0 ? "high" : i === 1 ? "medium" : "low",
            });
          }
        }

        res.json({ success: true, chunks });
        break;

      case "prioritize":
        // Simple prioritization based on keywords
        let priority = "medium";
        const urgentKeywords = [
          "urgent",
          "asap",
          "today",
          "now",
          "immediately",
        ];
        const importantKeywords = ["important", "critical", "key", "essential"];

        if (urgentKeywords.some((kw) => task.toLowerCase().includes(kw))) {
          priority = "urgent";
        } else if (
          importantKeywords.some((kw) => task.toLowerCase().includes(kw))
        ) {
          priority = "high";
        }

        res.json({ success: true, priority, task });
        break;

      case "energy_match":
        // Match task to energy levels
        const currentHour = new Date().getHours();
        let energyLevel = "medium";

        if (currentHour >= 9 && currentHour <= 11) {
          energyLevel = "high";
        } else if (currentHour >= 14 && currentHour <= 16) {
          energyLevel = "low";
        }

        res.json({
          success: true,
          current_energy: energyLevel,
          recommended:
            energyLevel === "high" ? "complex tasks" : "routine tasks",
        });
        break;

      default:
        res.status(400).json({ error: "Invalid operation" });
    }
  } catch (error) {
    logger.error("ADHD task operation failed:", error);
    res.status(500).json({ error: error.message });
  }
});

// Initialize on startup
const initialize = async () => {
  try {
    initializeRouting();
    initializeFamilyContext();
    registerAgents();

    // Load persisted memory if exists
    try {
      const memoryData = await fs.readFile("/app/state/memory.json", "utf8");
      const parsed = JSON.parse(memoryData);
      Object.entries(parsed).forEach(([key, value]) => {
        state.memory.set(key, value);
      });
      logger.info(`Loaded ${state.memory.size} memory items from disk`);
    } catch (err) {
      logger.info("No persisted memory found, starting fresh");
    }

    logger.info("EA-AI container initialized successfully");
  } catch (error) {
    logger.error("Initialization failed:", error);
  }
};

// Start server
const PORT = process.env.PORT || 8080;
app.listen(PORT, () => {
  logger.info(`EA-AI container listening on port ${PORT}`);
  initialize();
});

// Graceful shutdown
process.on("SIGTERM", async () => {
  logger.info("SIGTERM received, saving state...");

  // Persist memory before shutdown
  const memoryData = Object.fromEntries(state.memory);
  await fs.writeFile(
    "/app/state/memory.json",
    JSON.stringify(memoryData, null, 2),
  );

  process.exit(0);
});
