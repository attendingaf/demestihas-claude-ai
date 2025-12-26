import sqlite3 from 'sqlite3';
import { open } from 'sqlite';
import path from 'path';
import { fileURLToPath } from 'url';
import crypto from 'crypto';

const __dirname = path.dirname(fileURLToPath(import.meta.url));

class ConversationMemory {
  constructor() {
    this.db = null;
    this.currentSession = null;
  }

  async initialize() {
    this.db = await open({
      filename: path.join(__dirname, 'data', 'conversations.db'),
      driver: sqlite3.Database
    });

    // Create conversation tables
    await this.db.exec(`
      CREATE TABLE IF NOT EXISTS conversations (
        id TEXT PRIMARY KEY,
        session_id TEXT,
        user_message TEXT,
        assistant_response TEXT,
        tool_calls TEXT,
        memories_used TEXT,
        timestamp INTEGER DEFAULT (strftime('%s', 'now') * 1000),
        metadata TEXT
      );

      CREATE TABLE IF NOT EXISTS sessions (
        id TEXT PRIMARY KEY,
        started_at INTEGER,
        ended_at INTEGER,
        message_count INTEGER DEFAULT 0,
        summary TEXT,
        metadata TEXT
      );

      CREATE INDEX IF NOT EXISTS idx_conv_session ON conversations(session_id);
      CREATE INDEX IF NOT EXISTS idx_conv_timestamp ON conversations(timestamp DESC);
    `);
  }

  async startSession(metadata = {}) {
    await this.ensureInitialized();

    this.currentSession = {
      id: crypto.randomUUID(),
      started_at: Date.now(),
      metadata
    };

    await this.db.run(
      `INSERT INTO sessions (id, started_at, metadata) VALUES (?, ?, ?)`,
      [this.currentSession.id, this.currentSession.started_at, JSON.stringify(metadata)]
    );

    return this.currentSession.id;
  }

  async addConversation(userMessage, assistantResponse, extras = {}) {
    await this.ensureInitialized();

    if (!this.currentSession) {
      await this.startSession();
    }

    const id = crypto.randomUUID();

    await this.db.run(
      `INSERT INTO conversations
       (id, session_id, user_message, assistant_response, tool_calls, memories_used, metadata)
       VALUES (?, ?, ?, ?, ?, ?, ?)`,
      [
        id,
        this.currentSession.id,
        userMessage,
        assistantResponse,
        JSON.stringify(extras.toolCalls || []),
        JSON.stringify(extras.memoriesUsed || []),
        JSON.stringify(extras.metadata || {})
      ]
    );

    // Update session message count
    await this.db.run(
      `UPDATE sessions SET message_count = message_count + 1 WHERE id = ?`,
      [this.currentSession.id]
    );

    return id;
  }

  async getRecentConversations(limit = 10) {
    await this.ensureInitialized();

    const conversations = await this.db.all(
      `SELECT * FROM conversations
       ORDER BY timestamp DESC
       LIMIT ?`,
      [limit]
    );

    return conversations.map(c => ({
      ...c,
      tool_calls: JSON.parse(c.tool_calls || '[]'),
      memories_used: JSON.parse(c.memories_used || '[]'),
      metadata: JSON.parse(c.metadata || '{}')
    }));
  }

  async searchConversations(query, limit = 10) {
    await this.ensureInitialized();

    const pattern = `%${query.toLowerCase()}%`;

    const conversations = await this.db.all(
      `SELECT * FROM conversations
       WHERE LOWER(user_message) LIKE ?
          OR LOWER(assistant_response) LIKE ?
       ORDER BY timestamp DESC
       LIMIT ?`,
      [pattern, pattern, limit]
    );

    return conversations;
  }

  async endSession(summary = null) {
    if (!this.currentSession) return;

    await this.db.run(
      `UPDATE sessions
       SET ended_at = ?, summary = ?
       WHERE id = ?`,
      [Date.now(), summary, this.currentSession.id]
    );

    this.currentSession = null;
  }

  async ensureInitialized() {
    if (!this.db) {
      await this.initialize();
    }
  }
}

export default new ConversationMemory();
