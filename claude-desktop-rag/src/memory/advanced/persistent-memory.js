import winston from 'winston';
import { v4 as uuidv4 } from 'uuid';
import sqlite3 from 'sqlite3';
import { open } from 'sqlite';
import { config } from '../../../config/rag-config.js';
import path from 'path';
import { performance } from 'perf_hooks';

const logger = winston.createLogger({
  level: config.logging.level,
  format: winston.format.json(),
  transports: [
    new winston.transports.Console(),
    new winston.transports.File({ filename: config.logging.file })
  ]
});

class PersistentMemory {
  constructor() {
    this.db = null;
    this.userProfiles = new Map();
    this.projectContexts = new Map();
    this.consolidationQueue = [];
    this.bootstrapCache = new Map();
    this.cacheTimeout = 5 * 60 * 1000; // 5 minutes
    this.maxFactsPerUser = 1000;
    this.maxPatternsPerUser = 100;
  }

  async initialize() {
    logger.info('Initializing persistent memory...');
    
    // Open database connection
    this.db = await open({
      filename: path.join(path.dirname(config.database.sqlitePath), 'persistent_memory.db'),
      driver: sqlite3.Database
    });
    
    // Create tables
    await this.createTables();
    
    // Load active profiles
    await this.loadActiveProfiles();
    
    logger.info('Persistent memory initialized');
  }

  async createTables() {
    // User preferences table
    await this.db.exec(`
      CREATE TABLE IF NOT EXISTS user_preferences (
        user_id TEXT PRIMARY KEY,
        preferences TEXT,
        created_at INTEGER,
        updated_at INTEGER
      )
    `);
    
    // User facts table
    await this.db.exec(`
      CREATE TABLE IF NOT EXISTS user_facts (
        id TEXT PRIMARY KEY,
        user_id TEXT,
        fact TEXT,
        confidence REAL,
        source TEXT,
        created_at INTEGER,
        last_used INTEGER,
        use_count INTEGER DEFAULT 0,
        FOREIGN KEY (user_id) REFERENCES user_preferences(user_id)
      )
    `);
    
    // User patterns table
    await this.db.exec(`
      CREATE TABLE IF NOT EXISTS user_patterns (
        id TEXT PRIMARY KEY,
        user_id TEXT,
        pattern TEXT,
        frequency INTEGER,
        context TEXT,
        created_at INTEGER,
        last_seen INTEGER,
        FOREIGN KEY (user_id) REFERENCES user_preferences(user_id)
      )
    `);
    
    // Project contexts table
    await this.db.exec(`
      CREATE TABLE IF NOT EXISTS project_contexts (
        project_id TEXT PRIMARY KEY,
        context TEXT,
        created_at INTEGER,
        updated_at INTEGER
      )
    `);
    
    // Session summaries table
    await this.db.exec(`
      CREATE TABLE IF NOT EXISTS session_summaries (
        id TEXT PRIMARY KEY,
        user_id TEXT,
        session_data TEXT,
        facts_extracted INTEGER,
        patterns_identified INTEGER,
        created_at INTEGER,
        FOREIGN KEY (user_id) REFERENCES user_preferences(user_id)
      )
    `);
    
    // Create indexes
    await this.db.exec(`
      CREATE INDEX IF NOT EXISTS idx_user_facts_user_id ON user_facts(user_id);
      CREATE INDEX IF NOT EXISTS idx_user_facts_confidence ON user_facts(confidence);
      CREATE INDEX IF NOT EXISTS idx_user_patterns_user_id ON user_patterns(user_id);
      CREATE INDEX IF NOT EXISTS idx_user_patterns_frequency ON user_patterns(frequency);
      CREATE INDEX IF NOT EXISTS idx_session_summaries_user_id ON session_summaries(user_id);
    `);
  }

  async saveUserPreferences(userId, preferences) {
    const now = Date.now();
    
    await this.db.run(
      `INSERT OR REPLACE INTO user_preferences (user_id, preferences, created_at, updated_at)
       VALUES (?, ?, COALESCE((SELECT created_at FROM user_preferences WHERE user_id = ?), ?), ?)`,
      [userId, JSON.stringify(preferences), userId, now, now]
    );
    
    // Update cache
    this.userProfiles.set(userId, {
      preferences,
      facts: [],
      patterns: [],
      lastUpdated: now
    });
    
    // Invalidate bootstrap cache
    this.bootstrapCache.delete(userId);
    
    logger.debug('User preferences saved', { userId });
  }

  async saveProjectContext(projectId, context) {
    const now = Date.now();
    
    await this.db.run(
      `INSERT OR REPLACE INTO project_contexts (project_id, context, created_at, updated_at)
       VALUES (?, ?, COALESCE((SELECT created_at FROM project_contexts WHERE project_id = ?), ?), ?)`,
      [projectId, JSON.stringify(context), projectId, now, now]
    );
    
    this.projectContexts.set(projectId, {
      ...context,
      lastUpdated: now
    });
    
    logger.debug('Project context saved', { projectId });
  }

  async consolidateSession(userId, sessionData) {
    const startTime = performance.now();
    
    // Extract facts from session
    const facts = await this.extractFacts(sessionData);
    
    // Identify patterns
    const patterns = await this.identifyPatterns(sessionData);
    
    // Save facts
    for (const fact of facts) {
      await this.saveFact(userId, fact);
    }
    
    // Save patterns
    for (const pattern of patterns) {
      await this.savePattern(userId, pattern);
    }
    
    // Save session summary
    const summaryId = uuidv4();
    await this.db.run(
      `INSERT INTO session_summaries (id, user_id, session_data, facts_extracted, patterns_identified, created_at)
       VALUES (?, ?, ?, ?, ?, ?)`,
      [summaryId, userId, JSON.stringify(sessionData), facts.length, patterns.length, Date.now()]
    );
    
    // Prune old data if needed
    await this.pruneUserData(userId);
    
    const consolidationTime = performance.now() - startTime;
    
    logger.info('Session consolidated', {
      userId,
      facts: facts.length,
      patterns: patterns.length,
      time: `${consolidationTime.toFixed(2)}ms`
    });
    
    return {
      facts: facts.length,
      patterns: patterns.length,
      summaryId
    };
  }

  async extractFacts(sessionData) {
    const facts = [];
    
    // Extract facts from interactions
    if (sessionData.interactions) {
      for (const interaction of sessionData.interactions) {
        if (interaction.type === 'code' || interaction.type === 'solution') {
          facts.push({
            content: `User implemented: ${interaction.content}`,
            confidence: 0.8,
            source: 'interaction'
          });
        }
        
        if (interaction.type === 'error' && interaction.resolution) {
          facts.push({
            content: `Error resolution: ${interaction.resolution}`,
            confidence: 0.9,
            source: 'error_fix'
          });
        }
      }
    }
    
    // Extract explicit facts
    if (sessionData.facts) {
      for (const fact of sessionData.facts) {
        facts.push({
          content: fact,
          confidence: 1.0,
          source: 'explicit'
        });
      }
    }
    
    // Extract from learnings
    if (sessionData.learnings) {
      for (const learning of sessionData.learnings) {
        facts.push({
          content: learning,
          confidence: 0.7,
          source: 'learning'
        });
      }
    }
    
    return facts;
  }

  async identifyPatterns(sessionData) {
    const patterns = [];
    
    // Analyze interaction sequences
    if (sessionData.interactions && sessionData.interactions.length > 2) {
      const sequences = this.findSequences(sessionData.interactions);
      
      for (const seq of sequences) {
        patterns.push({
          pattern: seq.pattern,
          frequency: seq.count,
          context: seq.context
        });
      }
    }
    
    // Extract workflow patterns
    if (sessionData.workflows) {
      for (const workflow of sessionData.workflows) {
        patterns.push({
          pattern: `Workflow: ${workflow}`,
          frequency: 1,
          context: 'workflow'
        });
      }
    }
    
    return patterns;
  }

  findSequences(interactions) {
    const sequences = [];
    const sequenceMap = new Map();
    
    // Look for 2-3 interaction patterns
    for (let i = 0; i < interactions.length - 1; i++) {
      const pattern2 = `${interactions[i].type}->${interactions[i + 1].type}`;
      sequenceMap.set(pattern2, (sequenceMap.get(pattern2) || 0) + 1);
      
      if (i < interactions.length - 2) {
        const pattern3 = `${interactions[i].type}->${interactions[i + 1].type}->${interactions[i + 2].type}`;
        sequenceMap.set(pattern3, (sequenceMap.get(pattern3) || 0) + 1);
      }
    }
    
    // Filter patterns that occur more than once
    for (const [pattern, count] of sequenceMap.entries()) {
      if (count > 1) {
        sequences.push({
          pattern,
          count,
          context: 'interaction_sequence'
        });
      }
    }
    
    return sequences;
  }

  async saveFact(userId, fact) {
    const factId = uuidv4();
    const now = Date.now();
    
    await this.db.run(
      `INSERT INTO user_facts (id, user_id, fact, confidence, source, created_at, last_used)
       VALUES (?, ?, ?, ?, ?, ?, ?)`,
      [factId, userId, fact.content, fact.confidence, fact.source, now, now]
    );
    
    return factId;
  }

  async savePattern(userId, pattern) {
    const now = Date.now();
    
    // Check if pattern exists
    const existing = await this.db.get(
      `SELECT id, frequency FROM user_patterns WHERE user_id = ? AND pattern = ?`,
      [userId, pattern.pattern]
    );
    
    if (existing) {
      // Update frequency
      await this.db.run(
        `UPDATE user_patterns SET frequency = ?, last_seen = ? WHERE id = ?`,
        [existing.frequency + pattern.frequency, now, existing.id]
      );
      return existing.id;
    } else {
      // Insert new pattern
      const patternId = uuidv4();
      await this.db.run(
        `INSERT INTO user_patterns (id, user_id, pattern, frequency, context, created_at, last_seen)
         VALUES (?, ?, ?, ?, ?, ?, ?)`,
        [patternId, userId, pattern.pattern, pattern.frequency, pattern.context, now, now]
      );
      return patternId;
    }
  }

  async bootstrapSession(userId) {
    const startTime = performance.now();
    
    // Check cache
    const cached = this.bootstrapCache.get(userId);
    if (cached && Date.now() - cached.timestamp < this.cacheTimeout) {
      logger.debug('Using cached bootstrap for user', { userId });
      return cached.data;
    }
    
    // Load user preferences
    const prefsRow = await this.db.get(
      `SELECT preferences FROM user_preferences WHERE user_id = ?`,
      [userId]
    );
    
    const preferences = prefsRow ? JSON.parse(prefsRow.preferences) : {};
    
    // Load top facts
    const facts = await this.db.all(
      `SELECT fact, confidence FROM user_facts 
       WHERE user_id = ? 
       ORDER BY confidence DESC, use_count DESC, last_used DESC 
       LIMIT 20`,
      [userId]
    );
    
    // Load frequent patterns
    const patterns = await this.db.all(
      `SELECT pattern, frequency, context FROM user_patterns 
       WHERE user_id = ? 
       ORDER BY frequency DESC, last_seen DESC 
       LIMIT 10`,
      [userId]
    );
    
    // Load recent session summaries
    const summaries = await this.db.all(
      `SELECT session_data FROM session_summaries 
       WHERE user_id = ? 
       ORDER BY created_at DESC 
       LIMIT 3`,
      [userId]
    );
    
    const bootstrapData = {
      userId,
      preferences,
      facts: facts.map(f => ({ content: f.fact, confidence: f.confidence })),
      patterns: patterns.map(p => ({
        pattern: p.pattern,
        frequency: p.frequency,
        context: p.context
      })),
      recentSessions: summaries.map(s => JSON.parse(s.session_data)),
      bootstrapTime: performance.now() - startTime
    };
    
    // Cache the result
    this.bootstrapCache.set(userId, {
      data: bootstrapData,
      timestamp: Date.now()
    });
    
    logger.info('Session bootstrapped', {
      userId,
      facts: facts.length,
      patterns: patterns.length,
      time: `${bootstrapData.bootstrapTime.toFixed(2)}ms`
    });
    
    return bootstrapData;
  }

  async getUserMemories(userId) {
    const memories = [];
    
    // Get facts as memories
    const facts = await this.db.all(
      `SELECT * FROM user_facts WHERE user_id = ? ORDER BY last_used DESC`,
      [userId]
    );
    
    for (const fact of facts) {
      memories.push({
        id: fact.id,
        content: fact.fact,
        type: 'fact',
        confidence: fact.confidence,
        timestamp: fact.created_at,
        accessCount: fact.use_count
      });
    }
    
    // Get patterns as memories
    const patterns = await this.db.all(
      `SELECT * FROM user_patterns WHERE user_id = ? ORDER BY frequency DESC`,
      [userId]
    );
    
    for (const pattern of patterns) {
      memories.push({
        id: pattern.id,
        content: pattern.pattern,
        type: 'pattern',
        frequency: pattern.frequency,
        timestamp: pattern.created_at
      });
    }
    
    return memories;
  }

  async pruneUserData(userId) {
    // Remove low-confidence, unused facts
    await this.db.run(
      `DELETE FROM user_facts 
       WHERE user_id = ? 
       AND confidence < 0.3 
       AND use_count = 0 
       AND (? - last_used) > ?`,
      [userId, Date.now(), 30 * 24 * 60 * 60 * 1000] // 30 days
    );
    
    // Keep only top N facts
    const factCount = await this.db.get(
      `SELECT COUNT(*) as count FROM user_facts WHERE user_id = ?`,
      [userId]
    );
    
    if (factCount.count > this.maxFactsPerUser) {
      await this.db.run(
        `DELETE FROM user_facts 
         WHERE user_id = ? 
         AND id NOT IN (
           SELECT id FROM user_facts 
           WHERE user_id = ? 
           ORDER BY confidence DESC, use_count DESC, last_used DESC 
           LIMIT ?
         )`,
        [userId, userId, this.maxFactsPerUser]
      );
    }
    
    // Keep only top N patterns
    const patternCount = await this.db.get(
      `SELECT COUNT(*) as count FROM user_patterns WHERE user_id = ?`,
      [userId]
    );
    
    if (patternCount.count > this.maxPatternsPerUser) {
      await this.db.run(
        `DELETE FROM user_patterns 
         WHERE user_id = ? 
         AND id NOT IN (
           SELECT id FROM user_patterns 
           WHERE user_id = ? 
           ORDER BY frequency DESC, last_seen DESC 
           LIMIT ?
         )`,
        [userId, userId, this.maxPatternsPerUser]
      );
    }
    
    logger.debug('User data pruned', { userId });
  }

  async loadActiveProfiles() {
    // Load recently active user profiles
    const recentUsers = await this.db.all(
      `SELECT DISTINCT user_id FROM session_summaries 
       WHERE created_at > ? 
       ORDER BY created_at DESC 
       LIMIT 10`,
      [Date.now() - 7 * 24 * 60 * 60 * 1000] // Last 7 days
    );
    
    for (const user of recentUsers) {
      await this.bootstrapSession(user.user_id);
    }
    
    logger.debug(`Loaded ${recentUsers.length} active user profiles`);
  }

  async getMetrics() {
    const userCount = await this.db.get(
      `SELECT COUNT(DISTINCT user_id) as count FROM user_preferences`
    );
    
    const factCount = await this.db.get(
      `SELECT COUNT(*) as count, AVG(confidence) as avgConfidence FROM user_facts`
    );
    
    const patternCount = await this.db.get(
      `SELECT COUNT(*) as count, AVG(frequency) as avgFrequency FROM user_patterns`
    );
    
    const sessionCount = await this.db.get(
      `SELECT COUNT(*) as count, AVG(facts_extracted) as avgFacts FROM session_summaries`
    );
    
    // Calculate average bootstrap time from cache
    let avgBootstrapTime = 0;
    if (this.bootstrapCache.size > 0) {
      const times = Array.from(this.bootstrapCache.values())
        .map(c => c.data.bootstrapTime || 0);
      avgBootstrapTime = times.reduce((a, b) => a + b, 0) / times.length;
    }
    
    return {
      totalUsers: userCount.count,
      totalFacts: factCount.count,
      avgFactConfidence: factCount.avgConfidence || 0,
      totalPatterns: patternCount.count,
      avgPatternFrequency: patternCount.avgFrequency || 0,
      totalSessions: sessionCount.count,
      avgFactsPerSession: sessionCount.avgFacts || 0,
      factExtractionRate: sessionCount.avgFacts ? sessionCount.avgFacts / 10 : 0, // Assuming 10 interactions per session
      avgBootstrapTime,
      cacheHitRate: this.bootstrapCache.size / Math.max(userCount.count, 1)
    };
  }
}

export default new PersistentMemory();