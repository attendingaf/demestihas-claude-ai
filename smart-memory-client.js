/**
 * Smart Memory Client
 * Connects EA-AI tools to the MCP Smart Memory HTTP API
 */

class SmartMemoryClient {
  constructor(apiUrl = 'http://localhost:7778') {
    this.apiUrl = apiUrl;
    this.cache = new Map(); // Simple cache for recent operations
    this.cacheTTL = 5000; // 5 seconds cache
  }

  /**
   * Store a memory
   */
  async set(key, value, options = {}) {
    try {
      const memory = {
        content: typeof value === 'string' ? value : JSON.stringify(value),
        type: options.type || 'ea_ai_memory',
        importance: options.importance || 'medium',
        metadata: {
          key,
          category: options.category || 'general',
          timestamp: Date.now(),
          ...options.metadata
        }
      };

      const response = await fetch(`${this.apiUrl}/store`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json'
        },
        body: JSON.stringify(memory)
      });

      if (!response.ok) {
        throw new Error(`HTTP ${response.status}: ${response.statusText}`);
      }

      const result = await response.json();
      
      // Cache the stored value
      this.cache.set(key, {
        value,
        timestamp: Date.now(),
        id: result.id
      });

      console.log(`[SmartMemoryClient] Stored memory: ${key} -> ${result.id}`);
      return result;
    } catch (error) {
      console.error('[SmartMemoryClient] Store failed:', error);
      throw error;
    }
  }

  /**
   * Get a memory by key
   */
  async get(key) {
    try {
      // Check cache first
      const cached = this.cache.get(key);
      if (cached && (Date.now() - cached.timestamp) < this.cacheTTL) {
        return cached.value;
      }

      // Search for the key
      const response = await fetch(`${this.apiUrl}/context?q=${encodeURIComponent(key)}&limit=5`);
      
      if (!response.ok) {
        throw new Error(`HTTP ${response.status}: ${response.statusText}`);
      }

      const result = await response.json();
      
      // Find exact key match in metadata
      const exactMatch = result.memories.find(mem => 
        mem.metadata?.key === key
      );

      if (exactMatch) {
        let value;
        try {
          value = JSON.parse(exactMatch.content);
        } catch {
          value = exactMatch.content;
        }

        // Update cache
        this.cache.set(key, {
          value,
          timestamp: Date.now(),
          id: exactMatch.id
        });

        return value;
      }

      return null;
    } catch (error) {
      console.error('[SmartMemoryClient] Get failed:', error);
      return null;
    }
  }

  /**
   * Search memories
   */
  async search(query, options = {}) {
    try {
      const { limit = 10 } = options;
      const response = await fetch(`${this.apiUrl}/context?q=${encodeURIComponent(query)}&limit=${limit}`);
      
      if (!response.ok) {
        throw new Error(`HTTP ${response.status}: ${response.statusText}`);
      }

      const result = await response.json();
      
      // Convert to key-value pairs for compatibility
      const entries = result.memories.map(mem => {
        const key = mem.metadata?.key || mem.id;
        let value;
        try {
          value = JSON.parse(mem.content);
        } catch {
          value = mem.content;
        }
        return [key, value];
      });

      return entries;
    } catch (error) {
      console.error('[SmartMemoryClient] Search failed:', error);
      return [];
    }
  }

  /**
   * Get all memories as entries (for compatibility)
   */
  async entries() {
    try {
      // Get recent memories
      const response = await fetch(`${this.apiUrl}/context?q=&limit=100`);
      
      if (!response.ok) {
        throw new Error(`HTTP ${response.status}: ${response.statusText}`);
      }

      const result = await response.json();
      
      // Convert to entries format
      const entries = result.memories.map(mem => {
        const key = mem.metadata?.key || mem.id;
        let value;
        try {
          value = JSON.parse(mem.content);
        } catch {
          value = mem.content;
        }
        return [key, value];
      });

      return entries;
    } catch (error) {
      console.error('[SmartMemoryClient] Entries failed:', error);
      return [];
    }
  }

  /**
   * Get memory count
   */
  async size() {
    try {
      const response = await fetch(`${this.apiUrl}/health`);
      
      if (!response.ok) {
        throw new Error(`HTTP ${response.status}: ${response.statusText}`);
      }

      const result = await response.json();
      return result.stats?.totalMemories || 0;
    } catch (error) {
      console.error('[SmartMemoryClient] Size failed:', error);
      return 0;
    }
  }

  /**
   * Persist memories (handled automatically by the server)
   */
  async persist() {
    try {
      const response = await fetch(`${this.apiUrl}/health`);
      
      if (!response.ok) {
        throw new Error(`HTTP ${response.status}: ${response.statusText}`);
      }

      const result = await response.json();
      console.log('[SmartMemoryClient] Memory system status:', result.status);
      
      return {
        persisted: true,
        items: result.stats?.totalMemories || 0,
        status: result.status
      };
    } catch (error) {
      console.error('[SmartMemoryClient] Persist failed:', error);
      return {
        persisted: false,
        error: error.message
      };
    }
  }

  /**
   * Health check
   */
  async isHealthy() {
    try {
      const response = await fetch(`${this.apiUrl}/health`);
      return response.ok;
    } catch {
      return false;
    }
  }

  /**
   * Clear cache
   */
  clearCache() {
    this.cache.clear();
  }
}

module.exports = SmartMemoryClient;