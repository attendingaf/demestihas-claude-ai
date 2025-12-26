import path from 'path';
import { fileURLToPath } from 'url';

const __dirname = path.dirname(fileURLToPath(import.meta.url));

/**
 * RAG Memory Adapter
 * Adapts the full RAG system to work with MCP Smart Memory interface
 */
class RAGMemoryAdapter {
  constructor() {
    this.ragSystem = null;
    this.initialized = false;
  }

  async initialize() {
    if (this.initialized) return;

    try {
      // Import RAG system dynamically
      const ragSystemPath = path.join(__dirname, '../claude-desktop-rag/src/index.js');
      const { default: ragSystem } = await import(ragSystemPath);
      
      this.ragSystem = ragSystem;
      
      // Initialize the RAG system
      await this.ragSystem.initialize();
      
      this.initialized = true;
      console.error('[RAGMemoryAdapter] RAG system initialized successfully');
    } catch (error) {
      console.error('[RAGMemoryAdapter] Failed to initialize RAG system:', error);
      throw error;
    }
  }

  /**
   * Store a memory using RAG system
   */
  async store(memory) {
    await this.ensureInitialized();

    try {
      // Map MCP memory format to RAG format
      const ragMemory = {
        content: memory.content,
        interactionType: memory.type || 'note',
        metadata: {
          ...memory.metadata,
          originalType: memory.type,
          category: memory.category,
          importance: memory.importance,
          mcp_id: memory.id,
          timestamp: memory.timestamp || Date.now()
        },
        successScore: this.mapImportanceToScore(memory.importance)
      };

      const result = await this.ragSystem.storeMemory(memory.content, ragMemory);
      
      console.error(`[RAGMemoryAdapter] Stored memory: ${result.id}`);
      return { 
        success: true, 
        id: result.id, 
        timestamp: result.created_at || Date.now()
      };
    } catch (error) {
      console.error('[RAGMemoryAdapter] Store failed:', error);
      throw error;
    }
  }

  /**
   * Search memories using RAG system
   */
  async search(query, options = {}) {
    await this.ensureInitialized();

    try {
      const {
        limit = 10,
        type = null,
        includeFailures = true,
        threshold = 0.7
      } = options;

      // Use RAG system's retrieve context method
      const results = await this.ragSystem.retrieveContext(query, {
        limit,
        includePatterns: false,
        includeKnowledge: true
      });

      // Map RAG results back to MCP format
      const mcpResults = results.map(item => ({
        id: item.id,
        content: item.content,
        type: item.metadata?.originalType || item.interaction_type || 'note',
        category: item.metadata?.category || item.interaction_type || 'general',
        importance: this.mapScoreToImportance(item.success_score),
        metadata: {
          ...item.metadata,
          rag_score: item.score,
          similarity: item.score,
          source: 'rag-system'
        },
        timestamp: new Date(item.created_at).getTime(),
        similarity: item.score // For compatibility with existing search interface
      }));

      // Filter by type if specified
      let filtered = mcpResults;
      if (type) {
        filtered = mcpResults.filter(mem => mem.type === type);
      }

      // Filter out failures if requested
      if (!includeFailures) {
        filtered = filtered.filter(mem => mem.type !== 'error_fix');
      }

      // Apply similarity threshold
      filtered = filtered.filter(mem => mem.similarity >= threshold);

      console.error(`[RAGMemoryAdapter] Search found ${filtered.length} results for: ${query}`);
      return filtered;
    } catch (error) {
      console.error('[RAGMemoryAdapter] Search failed:', error);
      return [];
    }
  }

  /**
   * Get all memories (limited)
   */
  async getAll(options = {}) {
    await this.ensureInitialized();

    try {
      const { limit = 100, type = null } = options;

      // Get recent memories by searching with a broad query
      const results = await this.ragSystem.retrieveContext('', {
        limit: limit * 2, // Get more to filter
        includePatterns: false,
        includeKnowledge: true
      });

      // Map and filter results
      let mcpResults = results.map(item => ({
        id: item.id,
        content: item.content,
        type: item.metadata?.originalType || item.interaction_type || 'note',
        category: item.metadata?.category || item.interaction_type || 'general',
        importance: this.mapScoreToImportance(item.success_score),
        metadata: {
          ...item.metadata,
          source: 'rag-system'
        },
        timestamp: new Date(item.created_at).getTime()
      }));

      if (type) {
        mcpResults = mcpResults.filter(mem => mem.type === type);
      }

      return mcpResults.slice(0, limit);
    } catch (error) {
      console.error('[RAGMemoryAdapter] GetAll failed:', error);
      return [];
    }
  }

  /**
   * Get memory statistics
   */
  async getStats() {
    await this.ensureInitialized();

    try {
      const ragStats = await this.ragSystem.getStats();
      
      return {
        totalMemories: ragStats.memory?.local?.totalMemories || 0,
        uniqueTypes: ragStats.memory?.local?.uniqueTypes || 0,
        uniqueCategories: ragStats.memory?.local?.uniqueCategories || 0,
        memoryTypes: ragStats.memory?.local?.memoryTypes || {},
        recentMemories: ragStats.memory?.local?.recentMemories || 0,
        lastUpdated: Date.now(),
        source: 'rag-system',
        cloudStatus: ragStats.memory?.cloud ? 'connected' : 'disconnected'
      };
    } catch (error) {
      console.error('[RAGMemoryAdapter] GetStats failed:', error);
      return {
        totalMemories: 0,
        uniqueTypes: 0,
        uniqueCategories: 0,
        memoryTypes: {},
        recentMemories: 0,
        source: 'rag-system',
        error: error.message
      };
    }
  }

  /**
   * Delete a memory
   */
  async deleteMemory(id) {
    console.warn('[RAGMemoryAdapter] Delete not implemented in RAG system');
    return { success: false, reason: 'Delete not supported by RAG system' };
  }

  /**
   * Clear all memories
   */
  async clearAll() {
    console.warn('[RAGMemoryAdapter] Clear all not implemented in RAG system');
    return { success: false, reason: 'Clear all not supported by RAG system' };
  }

  /**
   * Map importance level to success score
   */
  mapImportanceToScore(importance) {
    switch (importance) {
      case 'critical': return 1.0;
      case 'high': return 0.8;
      case 'medium': return 0.6;
      case 'low': return 0.4;
      default: return 0.6;
    }
  }

  /**
   * Map success score to importance level
   */
  mapScoreToImportance(score) {
    if (!score || score < 0.5) return 'low';
    if (score < 0.7) return 'medium';
    if (score < 0.9) return 'high';
    return 'critical';
  }

  async ensureInitialized() {
    if (!this.initialized) {
      await this.initialize();
    }
  }
}

export default new RAGMemoryAdapter();