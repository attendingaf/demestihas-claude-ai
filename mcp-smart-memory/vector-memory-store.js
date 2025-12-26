/**
 * Vector Memory Store with Semantic Search
 * Enhances SimpleMemoryStore with OpenAI embeddings for semantic search
 */

import simpleMemoryStore from './simple-memory-store.js';
import OpenAI from 'openai';
import dotenv from 'dotenv';
import path from 'path';
import { fileURLToPath } from 'url';
import sqlite3 from 'sqlite3';
import { open } from 'sqlite';

const __dirname = path.dirname(fileURLToPath(import.meta.url));
dotenv.config({ path: path.join(__dirname, '../claude-desktop-rag/.env') });

class VectorMemoryStore {
  constructor() {
    this.baseStore = simpleMemoryStore;
    this.openai = null;
    this.db = null;
    this.initialized = false;
    this.embeddingCache = new Map();
  }

  async initialize() {
    // Initialize base store
    await this.baseStore.initialize();

    // Initialize OpenAI
    const apiKey = process.env.OPENAI_API_KEY || process.env.REACT_APP_OPENAI_API_KEY;
    if (apiKey && apiKey !== 'your-openai-api-key-here') {
      this.openai = new OpenAI({ apiKey });
      console.log('[VectorMemoryStore] OpenAI client initialized');
    } else {
      console.log('[VectorMemoryStore] No OpenAI API key found, falling back to keyword search only');
    }

    // Open direct database connection for vector operations
    this.db = await open({
      filename: path.join(__dirname, 'data', 'smart_memory.db'),
      driver: sqlite3.Database
    });

    // Add embedding column if it doesn't exist
    try {
      await this.db.exec(`
        ALTER TABLE memories ADD COLUMN embedding TEXT;
      `);
      console.log('[VectorMemoryStore] Added embedding column');
    } catch (error) {
      // Column likely already exists
    }

    // Create index for embeddings
    try {
      await this.db.exec(`
        CREATE INDEX IF NOT EXISTS idx_memories_embedding
        ON memories(id) WHERE embedding IS NOT NULL;
      `);
    } catch (error) {
      console.error('[VectorMemoryStore] Failed to create embedding index:', error);
    }

    this.initialized = true;

    // Process any unembedded memories in background
    this.processUnembeddedMemories();

    return { status: 'initialized', hasVectorSearch: !!this.openai };
  }

  async generateEmbedding(text) {
    if (!this.openai) return null;

    // Check cache first
    const cacheKey = text.substring(0, 100);
    if (this.embeddingCache.has(cacheKey)) {
      return this.embeddingCache.get(cacheKey);
    }

    try {
      const response = await this.openai.embeddings.create({
        model: "text-embedding-3-small",
        input: text.substring(0, 8000) // Limit input length
      });

      const embedding = response.data[0].embedding;

      // Cache for this session
      this.embeddingCache.set(cacheKey, embedding);

      return embedding;
    } catch (error) {
      console.error('[VectorMemoryStore] Embedding generation failed:', error.message);
      return null;
    }
  }

  async store(memory) {
    // Store normally first
    const result = await this.baseStore.store(memory);

    // Generate and store embedding
    if (this.openai && result.id) {
      const embedding = await this.generateEmbedding(memory.content);
      if (embedding) {
        try {
          await this.db.run(
            `UPDATE memories SET embedding = ? WHERE id = ?`,
            [JSON.stringify(embedding), result.id]
          );
          console.log(`[VectorMemoryStore] Stored embedding for ${result.id}`);
        } catch (error) {
          console.error('[VectorMemoryStore] Failed to store embedding:', error);
        }
      }
    }

    return result;
  }

  cosineSimilarity(vec1, vec2) {
    if (!vec1 || !vec2 || vec1.length !== vec2.length) return 0;

    let dotProduct = 0;
    let norm1 = 0;
    let norm2 = 0;

    for (let i = 0; i < vec1.length; i++) {
      dotProduct += vec1[i] * vec2[i];
      norm1 += vec1[i] * vec1[i];
      norm2 += vec2[i] * vec2[i];
    }

    norm1 = Math.sqrt(norm1);
    norm2 = Math.sqrt(norm2);

    if (norm1 === 0 || norm2 === 0) return 0;

    return dotProduct / (norm1 * norm2);
  }

  async semanticSearch(query, options = {}) {
    const { limit = 10, threshold = 0.3 } = options;

    // Generate query embedding
    const queryEmbedding = await this.generateEmbedding(query);
    if (!queryEmbedding) {
      console.log('[VectorMemoryStore] No query embedding, falling back to keyword search');
      return [];
    }

    // Get all memories with embeddings
    const memories = await this.db.all(`
      SELECT * FROM memories
      WHERE embedding IS NOT NULL
      ORDER BY timestamp DESC
      LIMIT 100
    `);

    // Calculate similarities
    const results = [];
    for (const memory of memories) {
      try {
        const embedding = JSON.parse(memory.embedding);
        const similarity = this.cosineSimilarity(queryEmbedding, embedding);

        if (similarity >= threshold) {
          results.push({
            ...memory,
            similarity,
            metadata: memory.metadata ? JSON.parse(memory.metadata) : {}
          });
        }
      } catch (error) {
        // Skip memories with invalid embeddings
      }
    }

    // Sort by similarity and return top results
    results.sort((a, b) => b.similarity - a.similarity);
    return results.slice(0, limit);
  }

  async search(query, options = {}) {
    const { limit = 10, hybridMode = true } = options;

    if (!this.openai) {
      // No OpenAI, use base keyword search
      return await this.baseStore.search(query, options);
    }

    if (!hybridMode) {
      // Semantic search only
      return await this.semanticSearch(query, options);
    }

    // Hybrid search: combine semantic and keyword results
    const [semanticResults, keywordResults] = await Promise.all([
      this.semanticSearch(query, { ...options, limit: limit * 2 }),
      this.baseStore.search(query, { ...options, limit: limit * 2 })
    ]);

    // Merge results with weighted scoring
    const mergedMap = new Map();

    // Add semantic results (60% weight)
    for (const result of semanticResults) {
      mergedMap.set(result.id, {
        ...result,
        score: result.similarity * 0.6,
        source: 'semantic'
      });
    }

    // Add/update with keyword results (40% weight)
    for (const result of keywordResults) {
      if (mergedMap.has(result.id)) {
        const existing = mergedMap.get(result.id);
        existing.score += result.similarity * 0.4;
        existing.source = 'hybrid';
      } else {
        mergedMap.set(result.id, {
          ...result,
          score: result.similarity * 0.4,
          source: 'keyword'
        });
      }
    }

    // Convert to array and sort by combined score
    const finalResults = Array.from(mergedMap.values())
      .sort((a, b) => b.score - a.score)
      .slice(0, limit)
      .map(result => ({
        ...result,
        similarity: result.score // Rename score back to similarity for API compatibility
      }));

    console.log(`[VectorMemoryStore] Hybrid search found ${finalResults.length} results (${semanticResults.length} semantic, ${keywordResults.length} keyword)`);
    return finalResults;
  }

  async processUnembeddedMemories() {
    if (!this.openai) return;

    try {
      // Find memories without embeddings
      const unembedded = await this.db.all(`
        SELECT id, content FROM memories
        WHERE embedding IS NULL
        LIMIT 10
      `);

      if (unembedded.length === 0) {
        console.log('[VectorMemoryStore] All memories have embeddings');
        return;
      }

      console.log(`[VectorMemoryStore] Processing ${unembedded.length} unembedded memories...`);

      for (const memory of unembedded) {
        const embedding = await this.generateEmbedding(memory.content);
        if (embedding) {
          await this.db.run(
            `UPDATE memories SET embedding = ? WHERE id = ?`,
            [JSON.stringify(embedding), memory.id]
          );
        }

        // Rate limit to avoid API throttling
        await new Promise(resolve => setTimeout(resolve, 100));
      }

      console.log('[VectorMemoryStore] Embedding processing complete');

      // Schedule next batch
      setTimeout(() => this.processUnembeddedMemories(), 30000);
    } catch (error) {
      console.error('[VectorMemoryStore] Failed to process unembedded memories:', error);
    }
  }

  // Delegate other methods to base store
  async getAll(options = {}) {
    return await this.baseStore.getAll(options);
  }

  async getStats() {
    const baseStats = await this.baseStore.getStats();

    // Add vector stats
    const embeddingCount = await this.db.get(`
      SELECT COUNT(*) as count FROM memories WHERE embedding IS NOT NULL
    `);

    return {
      ...baseStats,
      vectorSearchEnabled: !!this.openai,
      embeddedMemories: embeddingCount?.count || 0,
      embeddingCoverage: baseStats.totalMemories > 0
        ? ((embeddingCount?.count || 0) / baseStats.totalMemories * 100).toFixed(1) + '%'
        : '0%'
    };
  }

  async deleteMemory(id) {
    return await this.baseStore.deleteMemory(id);
  }

  async clearAll() {
    this.embeddingCache.clear();
    return await this.baseStore.clearAll();
  }

  async ensureInitialized() {
    if (!this.initialized) {
      await this.initialize();
    }
  }
}

// Export singleton instance
export default new VectorMemoryStore();
