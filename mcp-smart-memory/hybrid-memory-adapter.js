/**
 * Hybrid Memory Adapter
 * Uses SimpleMemoryStore for local SQLite storage and syncs to Supabase
 */

import simpleMemoryStore from "./simple-memory-store.js";
import vectorMemoryStore from "./vector-memory-store.js";
import { createClient } from "@supabase/supabase-js";
import dotenv from "dotenv";
import path from "path";
import { fileURLToPath } from "url";

const __dirname = path.dirname(fileURLToPath(import.meta.url));
dotenv.config({ path: path.join(__dirname, "../claude-desktop-rag/.env") });

class HybridMemoryAdapter {
  constructor() {
    // Use vector store for semantic search capabilities
    this.localStore = vectorMemoryStore;
    this.supabase = null;
    this.syncInterval = null;
    this.initialized = false;
  }

  async initialize() {
    // Initialize local store first
    await this.localStore.initialize();
    console.log("[HybridMemoryAdapter] Local store initialized");

    // Try to initialize Supabase
    try {
      const supabaseUrl = process.env.SUPABASE_URL;
      const supabaseKey = process.env.SUPABASE_ANON_KEY;

      if (supabaseUrl && supabaseKey) {
        this.supabase = createClient(supabaseUrl, supabaseKey);
        console.log("[HybridMemoryAdapter] Supabase client initialized");

        // Start sync interval (every 30 seconds)
        this.startSyncInterval();

        // Do initial sync
        await this.syncToCloud();
      } else {
        console.log(
          "[HybridMemoryAdapter] Supabase credentials not found, running local-only",
        );
      }
    } catch (error) {
      console.error(
        "[HybridMemoryAdapter] Failed to initialize Supabase:",
        error.message,
      );
      console.log("[HybridMemoryAdapter] Continuing with local-only mode");
    }

    this.initialized = true;
    return { status: "initialized", hasCloud: !!this.supabase };
  }

  startSyncInterval() {
    if (this.syncInterval) return;

    this.syncInterval = setInterval(async () => {
      await this.syncToCloud();
    }, 30000); // Sync every 30 seconds

    console.log("[HybridMemoryAdapter] Sync interval started (30s)");
  }

  async syncToCloud() {
    if (!this.supabase) return;

    try {
      // Get all memories from local store
      const localMemories = await this.localStore.getAll({ limit: 1000 });

      if (localMemories.length === 0) {
        console.log("[HybridMemoryAdapter] No memories to sync");
        return;
      }

      // Prepare memories for Supabase (minimal fields that exist in schema)
      const memoriesToSync = localMemories.map((mem) => ({
        id: mem.id,
        content: mem.content,
        type: mem.type || "note",
        metadata: mem.metadata || {},
        created_at: new Date(mem.timestamp).toISOString(),
        updated_at: new Date().toISOString(),
      }));

      // Batch upsert to Supabase
      const { data, error } = await this.supabase
        .from("project_memories")
        .upsert(memoriesToSync, {
          onConflict: "id",
          ignoreDuplicates: false,
        });

      if (error) {
        console.error("[HybridMemoryAdapter] Sync error:", error);
      } else {
        console.log(
          `[HybridMemoryAdapter] Synced ${memoriesToSync.length} memories to cloud`,
        );
      }
    } catch (error) {
      console.error("[HybridMemoryAdapter] Sync failed:", error);
    }
  }

  // Delegate all operations to local store
  async store(content, metadata = {}) {
    const result = await this.localStore.store(content, metadata);

    // Trigger immediate sync for new memories
    if (this.supabase && result.id) {
      setTimeout(() => this.syncToCloud(), 1000);
    }

    return result;
  }

  async search(query, options = {}) {
    // For now, search locally only
    // TODO: Implement hybrid search that combines local and cloud results
    return await this.localStore.search(query, options);
  }

  async getAll(options = {}) {
    return await this.localStore.getAll(options);
  }

  async getStats() {
    const localStats = await this.localStore.getStats();

    // Add cloud status to stats
    return {
      ...localStats,
      cloudStatus: this.supabase ? "connected" : "disconnected",
      syncEnabled: !!this.syncInterval,
    };
  }

  async deleteMemory(id) {
    // Delete from local
    const result = await this.localStore.deleteMemory(id);

    // Also delete from cloud if connected
    if (this.supabase && result.success) {
      try {
        await this.supabase.from("project_memories").delete().eq("id", id);
      } catch (error) {
        console.error(
          "[HybridMemoryAdapter] Failed to delete from cloud:",
          error,
        );
      }
    }

    return result;
  }

  async clearAll() {
    // Clear local
    const result = await this.localStore.clearAll();

    // Also clear cloud if connected
    if (this.supabase && result.success) {
      try {
        await this.supabase.from("project_memories").delete().neq("id", ""); // Delete all
      } catch (error) {
        console.error("[HybridMemoryAdapter] Failed to clear cloud:", error);
      }
    }

    return result;
  }

  async shutdown() {
    if (this.syncInterval) {
      clearInterval(this.syncInterval);
      this.syncInterval = null;
    }

    // Final sync before shutdown
    await this.syncToCloud();

    console.log("[HybridMemoryAdapter] Shutdown complete");
  }
}

// Export singleton instance
export default new HybridMemoryAdapter();
