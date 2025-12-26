import winston from 'winston';
import { v4 as uuidv4 } from 'uuid';
import { config } from '../../../config/rag-config.js';

const logger = winston.createLogger({
  level: config.logging.level,
  format: winston.format.json(),
  transports: [
    new winston.transports.Console(),
    new winston.transports.File({ filename: config.logging.file })
  ]
});

class EpisodicMemory {
  constructor() {
    this.episodes = new Map();
    this.sessions = new Map();
    this.causalChains = new Map();
    this.currentSession = null;
    this.sessionTimeout = 30 * 60 * 1000; // 30 minutes
    this.importanceThreshold = 0.5;
    this.maxEpisodesPerSession = 1000;
  }

  async initialize() {
    logger.info('Initializing episodic memory...');
    this.currentSession = await this.createSessionBoundary(Date.now());
    logger.info('Episodic memory initialized');
  }

  async recordEpisode(event, context) {
    const timestamp = Date.now();
    
    if (this.shouldStartNewSession(timestamp)) {
      await this.createSessionBoundary(timestamp);
    }
    
    const importance = await this.calculateImportance(event, context);
    
    const episode = {
      id: uuidv4(),
      sessionId: this.currentSession,
      timestamp,
      event,
      context: this.extractContext(context),
      importance,
      references: await this.findReferences(event),
      causalLinks: [],
      accessCount: 0,
      lastAccess: timestamp
    };
    
    // Establish causal links
    if (this.lastEpisode) {
      episode.causalLinks.push(this.lastEpisode.id);
      this.updateCausalChain(this.lastEpisode.id, episode.id);
    }
    
    this.episodes.set(episode.id, episode);
    this.lastEpisode = episode;
    
    // Update session
    const session = this.sessions.get(this.currentSession);
    if (session) {
      session.episodes.push(episode.id);
      session.lastActivity = timestamp;
    }
    
    logger.debug('Episode recorded', {
      id: episode.id,
      importance: importance.toFixed(2),
      sessionId: this.currentSession
    });
    
    return episode.id;
  }

  async recallEpisodes(criteria) {
    const { timeWindow, importance, context, limit = 10 } = criteria;
    
    let episodes = Array.from(this.episodes.values());
    
    // Apply time window filter
    if (timeWindow) {
      const cutoff = this.getTimeWindowCutoff(timeWindow);
      episodes = episodes.filter(e => e.timestamp > cutoff);
    }
    
    // Apply importance filter
    if (importance !== undefined) {
      episodes = episodes.filter(e => e.importance >= importance);
    }
    
    // Apply context similarity
    if (context) {
      episodes = await this.filterByContextSimilarity(episodes, context);
    }
    
    // Apply temporal decay
    episodes = this.applyTemporalDecay(episodes);
    
    // Sort by relevance
    episodes.sort((a, b) => {
      const scoreA = this.calculateRelevanceScore(a, criteria);
      const scoreB = this.calculateRelevanceScore(b, criteria);
      return scoreB - scoreA;
    });
    
    // Update access counts
    const results = episodes.slice(0, limit);
    results.forEach(episode => {
      episode.accessCount++;
      episode.lastAccess = Date.now();
    });
    
    return results;
  }

  async getCausalChain(event) {
    const relatedEpisodes = [];
    const visited = new Set();
    
    // Find starting episode
    const startEpisode = Array.from(this.episodes.values())
      .find(e => this.eventsMatch(e.event, event));
    
    if (!startEpisode) return [];
    
    // Traverse causal chain backwards
    const traverse = (episodeId) => {
      if (visited.has(episodeId)) return;
      visited.add(episodeId);
      
      const episode = this.episodes.get(episodeId);
      if (!episode) return;
      
      relatedEpisodes.unshift(episode);
      
      episode.causalLinks.forEach(linkId => traverse(linkId));
    };
    
    // Traverse forward from starting point
    const chain = this.causalChains.get(startEpisode.id);
    if (chain) {
      chain.forEach(id => {
        const episode = this.episodes.get(id);
        if (episode) relatedEpisodes.push(episode);
      });
    }
    
    // Traverse backward from starting point
    startEpisode.causalLinks.forEach(linkId => traverse(linkId));
    
    return relatedEpisodes;
  }

  async createSessionBoundary(timestamp) {
    const sessionId = uuidv4();
    
    // Consolidate previous session if exists
    if (this.currentSession) {
      await this.consolidateSession(this.currentSession);
    }
    
    const session = {
      id: sessionId,
      startTime: timestamp,
      lastActivity: timestamp,
      episodes: [],
      summary: null,
      consolidated: false
    };
    
    this.sessions.set(sessionId, session);
    this.currentSession = sessionId;
    this.lastEpisode = null;
    
    logger.info('New session boundary created', { sessionId });
    
    return sessionId;
  }

  shouldStartNewSession(timestamp) {
    if (!this.currentSession) return true;
    
    const session = this.sessions.get(this.currentSession);
    if (!session) return true;
    
    // Check timeout
    if (timestamp - session.lastActivity > this.sessionTimeout) {
      return true;
    }
    
    // Check episode limit
    if (session.episodes.length >= this.maxEpisodesPerSession) {
      return true;
    }
    
    return false;
  }

  async calculateImportance(event, context) {
    let importance = 0.5; // Base importance
    
    // Event type importance
    const eventTypeWeights = {
      error: 0.9,
      fix: 0.8,
      code_generation: 0.7,
      query: 0.6,
      command: 0.5
    };
    
    if (eventTypeWeights[event.type]) {
      importance = eventTypeWeights[event.type];
    }
    
    // Context modifiers
    if (context.userId) importance += 0.1;
    if (context.projectId) importance += 0.1;
    if (event.complexity === 'high') importance += 0.2;
    if (event.resolution) importance += 0.15;
    
    // Frequency-based adjustment
    const recentSimilar = await this.countRecentSimilar(event, 3600000); // 1 hour
    if (recentSimilar > 3) {
      importance *= 0.8; // Reduce importance for repetitive events
    }
    
    return Math.min(1.0, importance);
  }

  extractContext(context) {
    return {
      projectId: context.projectId,
      userId: context.userId,
      environment: context.environment,
      timestamp: Date.now(),
      metadata: context.metadata || {}
    };
  }

  async findReferences(event) {
    const references = [];
    
    // Find episodes with similar content
    const similarEpisodes = Array.from(this.episodes.values())
      .filter(e => this.calculateEventSimilarity(e.event, event) > 0.7)
      .slice(0, 5);
    
    references.push(...similarEpisodes.map(e => e.id));
    
    return references;
  }

  calculateEventSimilarity(event1, event2) {
    if (event1.type !== event2.type) return 0;
    
    let similarity = 0.3; // Base similarity for same type
    
    // Check property overlap
    const keys1 = Object.keys(event1);
    const keys2 = Object.keys(event2);
    const commonKeys = keys1.filter(k => keys2.includes(k));
    
    similarity += (commonKeys.length / Math.max(keys1.length, keys2.length)) * 0.3;
    
    // Check value similarity for common keys
    let valueSimilarity = 0;
    commonKeys.forEach(key => {
      if (event1[key] === event2[key]) {
        valueSimilarity += 1;
      }
    });
    
    if (commonKeys.length > 0) {
      similarity += (valueSimilarity / commonKeys.length) * 0.4;
    }
    
    return similarity;
  }

  eventsMatch(event1, event2) {
    return this.calculateEventSimilarity(event1, event2) > 0.8;
  }

  updateCausalChain(fromId, toId) {
    if (!this.causalChains.has(fromId)) {
      this.causalChains.set(fromId, []);
    }
    this.causalChains.get(fromId).push(toId);
  }

  getTimeWindowCutoff(window) {
    const now = Date.now();
    const windows = {
      recent: 5 * 60 * 1000,        // 5 minutes
      hour: 60 * 60 * 1000,          // 1 hour
      day: 24 * 60 * 60 * 1000,      // 1 day
      week: 7 * 24 * 60 * 60 * 1000  // 1 week
    };
    
    return now - (windows[window] || windows.day);
  }

  async filterByContextSimilarity(episodes, targetContext) {
    return episodes.filter(episode => {
      const similarity = this.calculateContextSimilarity(episode.context, targetContext);
      return similarity > 0.5;
    });
  }

  calculateContextSimilarity(context1, context2) {
    if (!context1 || !context2) return 0;
    
    let similarity = 0;
    let factors = 0;
    
    if (context1.projectId === context2.projectId) {
      similarity += 0.4;
      factors++;
    }
    
    if (context1.userId === context2.userId) {
      similarity += 0.3;
      factors++;
    }
    
    if (context1.environment === context2.environment) {
      similarity += 0.3;
      factors++;
    }
    
    return factors > 0 ? similarity / factors : 0;
  }

  applyTemporalDecay(episodes) {
    const now = Date.now();
    const halfLife = 7 * 24 * 60 * 60 * 1000; // 7 days
    
    return episodes.map(episode => {
      const age = now - episode.timestamp;
      const decayFactor = Math.exp(-age / halfLife);
      
      return {
        ...episode,
        adjustedImportance: episode.importance * decayFactor
      };
    });
  }

  calculateRelevanceScore(episode, criteria) {
    let score = episode.adjustedImportance || episode.importance;
    
    // Boost for recent access
    const recencyBoost = Math.exp(-(Date.now() - episode.lastAccess) / (24 * 60 * 60 * 1000));
    score += recencyBoost * 0.2;
    
    // Boost for high access count
    score += Math.min(episode.accessCount * 0.05, 0.3);
    
    // Boost for causal connections
    score += Math.min(episode.causalLinks.length * 0.1, 0.3);
    
    return score;
  }

  async countRecentSimilar(event, timeWindow) {
    const cutoff = Date.now() - timeWindow;
    
    return Array.from(this.episodes.values())
      .filter(e => e.timestamp > cutoff)
      .filter(e => this.calculateEventSimilarity(e.event, event) > 0.8)
      .length;
  }

  async consolidateSession(sessionId) {
    const session = this.sessions.get(sessionId);
    if (!session || session.consolidated) return;
    
    const episodes = session.episodes.map(id => this.episodes.get(id)).filter(Boolean);
    
    if (episodes.length === 0) return;
    
    // Generate session summary
    session.summary = {
      totalEpisodes: episodes.length,
      timespan: session.lastActivity - session.startTime,
      avgImportance: episodes.reduce((sum, e) => sum + e.importance, 0) / episodes.length,
      keyEvents: episodes
        .filter(e => e.importance > 0.7)
        .map(e => ({ type: e.event.type, timestamp: e.timestamp }))
    };
    
    session.consolidated = true;
    
    logger.info('Session consolidated', {
      sessionId,
      episodes: session.summary.totalEpisodes,
      duration: `${(session.summary.timespan / 1000 / 60).toFixed(1)} minutes`
    });
  }

  async getMetrics() {
    const episodes = Array.from(this.episodes.values());
    const sessions = Array.from(this.sessions.values());
    
    return {
      totalEpisodes: episodes.length,
      activeSessions: sessions.filter(s => !s.consolidated).length,
      avgImportance: episodes.length > 0 
        ? episodes.reduce((sum, e) => sum + e.importance, 0) / episodes.length 
        : 0,
      avgSessionLength: sessions.length > 0
        ? sessions.reduce((sum, s) => sum + s.episodes.length, 0) / sessions.length
        : 0,
      causalChains: this.causalChains.size,
      memoryUsage: this.estimateMemoryUsage()
    };
  }

  estimateMemoryUsage() {
    // Rough estimation of memory usage in MB
    const episodeSize = 2 * 1024; // ~2KB per episode
    const sessionSize = 512; // ~0.5KB per session
    
    const totalSize = (this.episodes.size * episodeSize) + (this.sessions.size * sessionSize);
    
    return (totalSize / 1024 / 1024).toFixed(2);
  }
}

export default new EpisodicMemory();