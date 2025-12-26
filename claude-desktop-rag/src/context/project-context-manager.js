import winston from 'winston';
import crypto from 'crypto';
import { config } from '../../config/rag-config.js';
import sqliteClient from '../core/sqlite-client-optimized.js';

const logger = winston.createLogger({
  level: config.logging.level,
  format: winston.format.json(),
  transports: [
    new winston.transports.Console(),
    new winston.transports.File({ filename: config.logging.file })
  ]
});

class ProjectContextManager {
  constructor() {
    this.currentProjectId = config.project.id;
    this.projectContexts = new Map();
    this.patternSpaces = new Map();
    this.switchTime = null;
    this.contextMetrics = {
      switchTimes: [],
      avgSwitchTime: 0
    };
  }

  async initialize() {
    try {
      // Load initial project context
      await this.loadProjectContext(this.currentProjectId);
      logger.info('Project Context Manager initialized', { 
        projectId: this.currentProjectId 
      });
    } catch (error) {
      logger.error('Failed to initialize Project Context Manager', { 
        error: error.message 
      });
      throw error;
    }
  }

  async loadProjectContext(projectId) {
    const startTime = Date.now();
    
    if (this.projectContexts.has(projectId)) {
      // Context already loaded, just activate it
      this.currentProjectId = projectId;
      this.trackSwitchTime(Date.now() - startTime);
      return this.projectContexts.get(projectId);
    }

    try {
      // Load project-specific memories
      const memories = await this.getProjectMemories(projectId, 100);
      
      // Load project-specific patterns
      const patterns = await this.getProjectPatterns(projectId);
      
      // Load project-specific settings
      const settings = await this.getProjectSettings(projectId);
      
      // Create context object
      const context = {
        projectId,
        memories,
        patterns,
        settings,
        similarityThreshold: settings.similarityThreshold || config.rag.similarityThreshold,
        patternSpace: new Map(),
        loadedAt: Date.now(),
        lastAccessed: Date.now()
      };

      // Build pattern space for quick lookup
      for (const pattern of patterns) {
        context.patternSpace.set(pattern.pattern_hash, pattern);
      }

      // Store in memory
      this.projectContexts.set(projectId, context);
      this.patternSpaces.set(projectId, context.patternSpace);
      
      // Track metrics
      this.trackSwitchTime(Date.now() - startTime);
      
      logger.debug('Project context loaded', {
        projectId,
        memories: memories.length,
        patterns: patterns.length,
        time: Date.now() - startTime
      });

      return context;
    } catch (error) {
      logger.error('Failed to load project context', {
        projectId,
        error: error.message
      });
      throw error;
    }
  }

  async switchProject(projectId) {
    const startTime = Date.now();
    
    if (projectId === this.currentProjectId) {
      logger.debug('Already on project', { projectId });
      return this.projectContexts.get(projectId);
    }

    try {
      // Save current context state if needed
      if (this.currentProjectId && this.projectContexts.has(this.currentProjectId)) {
        await this.saveContextState(this.currentProjectId);
      }

      // Load new project context
      const context = await this.loadProjectContext(projectId);
      
      // Update current project
      this.currentProjectId = projectId;
      
      // Update config (for other modules)
      config.project.id = projectId;
      
      // Clear caches that might have cross-project data
      await this.clearProjectCaches();
      
      const switchTime = Date.now() - startTime;
      this.trackSwitchTime(switchTime);
      
      logger.info('Project context switched', {
        from: this.currentProjectId,
        to: projectId,
        time: switchTime
      });

      return context;
    } catch (error) {
      logger.error('Failed to switch project context', {
        projectId,
        error: error.message
      });
      throw error;
    }
  }

  async getContextForQuery(query, projectId = null) {
    const pid = projectId || this.currentProjectId;
    
    // Ensure context is loaded
    if (!this.projectContexts.has(pid)) {
      await this.loadProjectContext(pid);
    }

    const context = this.projectContexts.get(pid);
    
    // Update last accessed
    context.lastAccessed = Date.now();
    
    return {
      projectId: pid,
      similarityThreshold: context.similarityThreshold,
      patterns: context.patterns,
      recentMemories: context.memories.slice(0, 20),
      settings: context.settings
    };
  }

  async searchWithContext(embedding, options = {}) {
    const {
      projectId = this.currentProjectId,
      includePatterns = true,
      contextBoost = true
    } = options;

    // Get project context
    const context = await this.getContextForQuery('', projectId);
    
    // Search with project-specific settings
    const searchOptions = {
      ...options,
      projectId,
      similarityThreshold: context.similarityThreshold
    };

    // Add context boost if enabled
    if (contextBoost) {
      searchOptions.contextBoost = this.calculateContextBoost(embedding, context);
    }

    // Perform search
    const results = await sqliteClient.searchMemories(embedding, searchOptions);
    
    // Add patterns if requested
    if (includePatterns) {
      const relevantPatterns = await this.findRelevantPatterns(embedding, context);
      results.patterns = relevantPatterns;
    }

    return results;
  }

  calculateContextBoost(embedding, context) {
    // Calculate boost based on recent context
    let boost = 1.0;
    
    // Check similarity with recent memories
    if (context.recentMemories && context.recentMemories.length > 0) {
      const recentSimilarity = this.averageSimilarity(
        embedding, 
        context.recentMemories.map(m => m.embedding)
      );
      
      if (recentSimilarity > 0.7) {
        boost *= 1.2; // 20% boost for high relevance to recent context
      }
    }
    
    return boost;
  }

  async findRelevantPatterns(embedding, context) {
    const relevantPatterns = [];
    const patternSpace = this.patternSpaces.get(context.projectId);
    
    if (!patternSpace) return relevantPatterns;

    for (const [hash, pattern] of patternSpace) {
      if (pattern.trigger_embedding) {
        const similarity = sqliteClient.cosineSimilarity(
          embedding,
          pattern.trigger_embedding
        );
        
        if (similarity >= context.similarityThreshold) {
          relevantPatterns.push({
            ...pattern,
            similarity
          });
        }
      }
    }

    // Sort by similarity
    relevantPatterns.sort((a, b) => b.similarity - a.similarity);
    
    return relevantPatterns.slice(0, 5); // Top 5 patterns
  }

  async isolateContext(projectId) {
    // Ensure complete isolation of project context
    const context = await this.loadProjectContext(projectId);
    
    // Create isolated search function
    const isolatedSearch = async (embedding, options = {}) => {
      // Force project ID
      options.projectId = projectId;
      
      // Ensure no cross-contamination
      const results = await sqliteClient.searchMemories(embedding, options);
      
      // Filter results to ensure they belong to the project
      return results.filter(r => r.project_id === projectId);
    };

    return {
      context,
      search: isolatedSearch,
      patterns: context.patterns,
      settings: context.settings
    };
  }

  async getProjectMemories(projectId, limit = 100) {
    const sql = `
      SELECT id, content, embedding_json, metadata, created_at,
             file_paths, tool_chain, success_score, last_accessed
      FROM project_memories_cache
      WHERE project_id = ?
      ORDER BY last_accessed DESC, created_at DESC
      LIMIT ?
    `;

    try {
      const rows = await sqliteClient.db.all(sql, [projectId, limit]);
      
      return rows.map(row => ({
        ...row,
        embedding: JSON.parse(row.embedding_json || '[]'),
        metadata: JSON.parse(row.metadata || '{}'),
        file_paths: JSON.parse(row.file_paths || '[]'),
        tool_chain: JSON.parse(row.tool_chain || '[]')
      }));
    } catch (error) {
      logger.error('Failed to get project memories', {
        projectId,
        error: error.message
      });
      return [];
    }
  }

  async getProjectPatterns(projectId) {
    const sql = `
      SELECT * FROM workflow_patterns_cache
      WHERE project_contexts LIKE ?
      ORDER BY occurrence_count DESC, last_used DESC
    `;

    try {
      const rows = await sqliteClient.db.all(sql, [`%"${projectId}"%`]);
      
      return rows.map(row => ({
        ...row,
        trigger_embedding: JSON.parse(row.trigger_embedding_json || '[]'),
        action_sequence: JSON.parse(row.action_sequence || '[]'),
        project_contexts: JSON.parse(row.project_contexts || '[]')
      }));
    } catch (error) {
      logger.error('Failed to get project patterns', {
        projectId,
        error: error.message
      });
      return [];
    }
  }

  async getProjectSettings(projectId) {
    // Load project-specific settings from database or config
    const sql = `
      SELECT settings FROM project_settings
      WHERE project_id = ?
    `;

    try {
      const row = await sqliteClient.db.get(sql, [projectId]);
      
      if (row && row.settings) {
        return JSON.parse(row.settings);
      }
    } catch (error) {
      // Table might not exist yet, use defaults
    }

    // Return default settings
    return {
      similarityThreshold: config.rag.similarityThreshold,
      maxContextItems: config.rag.maxContextItems,
      patternDetectionThreshold: 3,
      autoApplyPatterns: false
    };
  }

  async saveProjectSettings(projectId, settings) {
    const sql = `
      INSERT OR REPLACE INTO project_settings (project_id, settings, updated_at)
      VALUES (?, ?, ?)
    `;

    try {
      await sqliteClient.db.run(sql, [
        projectId,
        JSON.stringify(settings),
        Math.floor(Date.now() / 1000)
      ]);
      
      // Update in-memory context if loaded
      if (this.projectContexts.has(projectId)) {
        const context = this.projectContexts.get(projectId);
        context.settings = settings;
        context.similarityThreshold = settings.similarityThreshold || config.rag.similarityThreshold;
      }
      
      logger.debug('Project settings saved', { projectId });
    } catch (error) {
      logger.error('Failed to save project settings', {
        projectId,
        error: error.message
      });
      throw error;
    }
  }

  async saveContextState(projectId) {
    const context = this.projectContexts.get(projectId);
    
    if (!context) return;

    try {
      // Save any pending changes
      // This is a placeholder for future state persistence
      logger.debug('Context state saved', { projectId });
    } catch (error) {
      logger.warn('Failed to save context state', {
        projectId,
        error: error.message
      });
    }
  }

  async clearProjectCaches() {
    // Clear any caches that might contain cross-project data
    // This is handled by the optimized SQLite client
    if (sqliteClient.searchCache) {
      sqliteClient.searchCache.clear();
    }
    if (sqliteClient.queryCache) {
      sqliteClient.queryCache.clear();
    }
  }

  averageSimilarity(embedding, embeddings) {
    if (!embeddings || embeddings.length === 0) return 0;
    
    let totalSimilarity = 0;
    let validCount = 0;
    
    for (const emb of embeddings) {
      if (emb && emb.length === embedding.length) {
        totalSimilarity += sqliteClient.cosineSimilarity(embedding, emb);
        validCount++;
      }
    }
    
    return validCount > 0 ? (totalSimilarity / validCount) : 0;
  }

  trackSwitchTime(time) {
    this.contextMetrics.switchTimes.push(time);
    
    // Keep only last 50 times
    if (this.contextMetrics.switchTimes.length > 50) {
      this.contextMetrics.switchTimes.shift();
    }
    
    // Calculate average
    this.contextMetrics.avgSwitchTime = 
      this.contextMetrics.switchTimes.reduce((a, b) => a + b, 0) / 
      this.contextMetrics.switchTimes.length;
    
    // Warn if exceeding target
    if (time > 100) {
      logger.warn('Context switch time exceeding target', { time });
    }
  }

  async getMetrics() {
    return {
      currentProject: this.currentProjectId,
      loadedContexts: this.projectContexts.size,
      avgSwitchTime: this.contextMetrics.avgSwitchTime,
      recentSwitchTimes: this.contextMetrics.switchTimes.slice(-10),
      contexts: Array.from(this.projectContexts.keys()).map(pid => ({
        projectId: pid,
        loadedAt: this.projectContexts.get(pid).loadedAt,
        lastAccessed: this.projectContexts.get(pid).lastAccessed,
        memoriesCount: this.projectContexts.get(pid).memories.length,
        patternsCount: this.projectContexts.get(pid).patterns.length
      }))
    };
  }

  async cleanup() {
    // Clean up old contexts that haven't been accessed recently
    const cutoff = Date.now() - (2 * 60 * 60 * 1000); // 2 hours
    
    for (const [projectId, context] of this.projectContexts) {
      if (projectId !== this.currentProjectId && context.lastAccessed < cutoff) {
        await this.saveContextState(projectId);
        this.projectContexts.delete(projectId);
        this.patternSpaces.delete(projectId);
        logger.debug('Cleaned up old project context', { projectId });
      }
    }
  }

  startCleanupTimer() {
    // Clean up every 30 minutes
    setInterval(() => {
      this.cleanup();
    }, 30 * 60 * 1000);
  }
}

export default new ProjectContextManager();