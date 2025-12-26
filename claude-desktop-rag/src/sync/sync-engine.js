import winston from 'winston';
import { config } from '../../config/rag-config.js';
import sqliteClient from '../core/sqlite-client-optimized.js';
import supabaseClient from '../core/supabase-client.js';

const logger = winston.createLogger({
  level: config.logging.level,
  format: winston.format.json(),
  transports: [
    new winston.transports.Console(),
    new winston.transports.File({ filename: config.logging.file })
  ]
});

class SyncEngine {
  constructor() {
    this.syncInProgress = false;
    this.syncInterval = null;
    this.realtimeSubscription = null;
    this.syncQueue = [];
    this.conflictResolutionStrategy = 'local-wins-recent';
    this.lastSyncTime = null;
    this.syncMetrics = {
      totalSyncs: 0,
      successfulSyncs: 0,
      failedSyncs: 0,
      conflictsResolved: 0,
      avgSyncTime: 0,
      syncTimes: []
    };
    this.offlineQueue = [];
    this.isOnline = true;
  }

  async initialize() {
    try {
      // Initialize SQLite client
      await sqliteClient.initialize();
      
      // Check Supabase connection
      await this.checkConnection();
      
      // Setup realtime subscriptions
      await this.setupRealtimeSync();
      
      // Start periodic sync
      this.startPeriodicSync();
      
      // Setup offline detection
      this.setupOfflineDetection();
      
      logger.info('Sync Engine initialized');
    } catch (error) {
      logger.error('Failed to initialize Sync Engine', { 
        error: error.message 
      });
      throw error;
    }
  }

  async checkConnection() {
    try {
      const { data, error } = await supabaseClient
        .from('project_memories')
        .select('id')
        .limit(1);
      
      if (error) throw error;
      
      this.isOnline = true;
      return true;
    } catch (error) {
      this.isOnline = false;
      logger.warn('Supabase connection unavailable', { 
        error: error.message 
      });
      return false;
    }
  }

  async setupRealtimeSync() {
    if (!this.isOnline) return;

    try {
      // Subscribe to changes in project_memories table
      this.realtimeSubscription = supabaseClient
        .channel('sync-channel')
        .on(
          'postgres_changes',
          {
            event: '*',
            schema: 'public',
            table: 'project_memories',
            filter: `project_id=eq.${config.project.id}`
          },
          (payload) => this.handleRealtimeChange(payload)
        )
        .on(
          'postgres_changes',
          {
            event: '*',
            schema: 'public',
            table: 'workflow_patterns',
            filter: `project_contexts@>${config.project.id}`
          },
          (payload) => this.handleRealtimeChange(payload)
        )
        .subscribe();

      logger.info('Realtime sync subscriptions setup');
    } catch (error) {
      logger.error('Failed to setup realtime sync', { 
        error: error.message 
      });
    }
  }

  async handleRealtimeChange(payload) {
    const { eventType, table, new: newRecord, old: oldRecord } = payload;
    
    logger.debug('Realtime change received', { 
      eventType, 
      table, 
      recordId: newRecord?.id || oldRecord?.id 
    });

    try {
      switch (eventType) {
        case 'INSERT':
          await this.handleRemoteInsert(table, newRecord);
          break;
        case 'UPDATE':
          await this.handleRemoteUpdate(table, newRecord, oldRecord);
          break;
        case 'DELETE':
          await this.handleRemoteDelete(table, oldRecord);
          break;
      }
    } catch (error) {
      logger.error('Failed to handle realtime change', { 
        error: error.message,
        eventType,
        table 
      });
    }
  }

  async handleRemoteInsert(table, record) {
    // Check if record exists locally
    const localRecord = await this.getLocalRecord(table, record.id);
    
    if (!localRecord) {
      // Insert into local database
      await this.insertLocalRecord(table, record);
      logger.debug('Remote insert synced to local', { 
        table, 
        id: record.id 
      });
    } else {
      // Conflict: record exists locally
      await this.resolveConflict(table, localRecord, record);
    }
  }

  async handleRemoteUpdate(table, newRecord, oldRecord) {
    const localRecord = await this.getLocalRecord(table, newRecord.id);
    
    if (localRecord) {
      // Check if local record is newer
      const localTime = new Date(localRecord.updated_at || localRecord.created_at).getTime();
      const remoteTime = new Date(newRecord.updated_at || newRecord.created_at).getTime();
      
      if (this.conflictResolutionStrategy === 'local-wins-recent') {
        if (localTime > remoteTime) {
          // Local is newer, push to remote
          await this.pushToRemote(table, localRecord);
        } else {
          // Remote is newer, update local
          await this.updateLocalRecord(table, newRecord);
        }
      } else {
        // Remote wins strategy
        await this.updateLocalRecord(table, newRecord);
      }
    } else {
      // No local record, insert it
      await this.insertLocalRecord(table, newRecord);
    }
  }

  async handleRemoteDelete(table, record) {
    await this.deleteLocalRecord(table, record.id);
    logger.debug('Remote delete synced to local', { 
      table, 
      id: record.id 
    });
  }

  async syncAll() {
    if (this.syncInProgress) {
      logger.debug('Sync already in progress, skipping');
      return;
    }

    const startTime = Date.now();
    this.syncInProgress = true;
    
    try {
      // Check connection first
      const isOnline = await this.checkConnection();
      
      if (!isOnline) {
        logger.info('Offline mode: queuing sync operations');
        return;
      }

      // Process offline queue first
      if (this.offlineQueue.length > 0) {
        await this.processOfflineQueue();
      }

      // Sync memories
      await this.syncMemories();
      
      // Sync patterns
      await this.syncPatterns();
      
      // Process sync queue
      await this.processSyncQueue();
      
      // Update last sync time
      this.lastSyncTime = Date.now();
      
      // Track metrics
      const syncTime = Date.now() - startTime;
      this.trackSyncMetrics(true, syncTime);
      
      logger.info('Sync completed', { 
        duration: syncTime,
        timestamp: this.lastSyncTime 
      });
    } catch (error) {
      logger.error('Sync failed', { error: error.message });
      this.trackSyncMetrics(false, Date.now() - startTime);
    } finally {
      this.syncInProgress = false;
    }
  }

  async syncMemories() {
    const localMemories = await this.getUnsyncedMemories();
    
    if (localMemories.length === 0) {
      logger.debug('No unsynced memories');
      return;
    }

    logger.debug('Syncing memories', { count: localMemories.length });

    for (const memory of localMemories) {
      try {
        const { data, error } = await supabaseClient
          .from('project_memories')
          .upsert({
            id: memory.id,
            project_id: memory.project_id,
            content: memory.content,
            embedding: memory.embedding_json ? JSON.parse(memory.embedding_json) : null,
            metadata: memory.metadata ? JSON.parse(memory.metadata) : {},
            interaction_type: memory.interaction_type,
            tool_chain: memory.tool_chain ? JSON.parse(memory.tool_chain) : [],
            file_paths: memory.file_paths ? JSON.parse(memory.file_paths) : [],
            success_score: memory.success_score,
            created_at: new Date(memory.created_at * 1000).toISOString(),
            session_id: memory.session_id,
            user_id: memory.user_id
          }, {
            onConflict: 'id'
          });

        if (error) throw error;

        // Mark as synced
        await sqliteClient.db.run(
          'UPDATE project_memories_cache SET synced_to_cloud = 1 WHERE id = ?',
          [memory.id]
        );
      } catch (error) {
        logger.error('Failed to sync memory', { 
          id: memory.id,
          error: error.message 
        });
        
        // Add to offline queue if offline
        if (!this.isOnline) {
          this.offlineQueue.push({
            type: 'memory',
            operation: 'upsert',
            data: memory
          });
        }
      }
    }
  }

  async syncPatterns() {
    const localPatterns = await this.getUnsyncedPatterns();
    
    if (localPatterns.length === 0) {
      logger.debug('No unsynced patterns');
      return;
    }

    logger.debug('Syncing patterns', { count: localPatterns.length });

    for (const pattern of localPatterns) {
      try {
        const { data, error } = await supabaseClient
          .from('workflow_patterns')
          .upsert({
            id: pattern.id,
            pattern_hash: pattern.pattern_hash,
            pattern_name: pattern.pattern_name,
            trigger_embedding: pattern.trigger_embedding_json ? 
              JSON.parse(pattern.trigger_embedding_json) : null,
            action_sequence: pattern.action_sequence ? 
              JSON.parse(pattern.action_sequence) : [],
            occurrence_count: pattern.occurrence_count,
            success_rate: pattern.success_rate,
            last_used: new Date(pattern.last_used * 1000).toISOString(),
            project_contexts: pattern.project_contexts ? 
              JSON.parse(pattern.project_contexts) : [],
            auto_apply: pattern.auto_apply === 1
          }, {
            onConflict: 'id'
          });

        if (error) throw error;

        // Mark as synced
        await sqliteClient.db.run(
          'UPDATE workflow_patterns_cache SET synced_to_cloud = 1 WHERE id = ?',
          [pattern.id]
        );
      } catch (error) {
        logger.error('Failed to sync pattern', { 
          id: pattern.id,
          error: error.message 
        });
        
        // Add to offline queue if offline
        if (!this.isOnline) {
          this.offlineQueue.push({
            type: 'pattern',
            operation: 'upsert',
            data: pattern
          });
        }
      }
    }
  }

  async processSyncQueue() {
    const queueItems = await sqliteClient.getSyncQueue(50);
    
    if (queueItems.length === 0) return;

    logger.debug('Processing sync queue', { count: queueItems.length });

    for (const item of queueItems) {
      try {
        const payload = JSON.parse(item.payload);
        
        switch (item.table_name) {
          case 'project_memories':
            await this.syncMemoryToCloud(payload);
            break;
          case 'workflow_patterns':
            await this.syncPatternToCloud(payload);
            break;
        }

        // Mark as completed
        await sqliteClient.markSyncCompleted(item.id);
      } catch (error) {
        logger.error('Failed to process sync queue item', { 
          id: item.id,
          error: error.message 
        });
      }
    }
  }

  async processOfflineQueue() {
    logger.info('Processing offline queue', { 
      count: this.offlineQueue.length 
    });

    const queue = [...this.offlineQueue];
    this.offlineQueue = [];

    for (const item of queue) {
      try {
        switch (item.type) {
          case 'memory':
            await this.syncMemoryToCloud(item.data);
            break;
          case 'pattern':
            await this.syncPatternToCloud(item.data);
            break;
        }
      } catch (error) {
        logger.error('Failed to process offline queue item', { 
          error: error.message 
        });
        // Re-add to queue if still offline
        if (!this.isOnline) {
          this.offlineQueue.push(item);
        }
      }
    }
  }

  async syncMemoryToCloud(memory) {
    const { data, error } = await supabaseClient
      .from('project_memories')
      .upsert({
        id: memory.id,
        project_id: memory.project_id,
        content: memory.content,
        embedding: memory.embedding,
        metadata: memory.metadata,
        interaction_type: memory.interaction_type,
        tool_chain: memory.tool_chain,
        file_paths: memory.file_paths,
        success_score: memory.success_score,
        created_at: memory.created_at,
        session_id: memory.session_id,
        user_id: memory.user_id
      }, {
        onConflict: 'id'
      });

    if (error) throw error;
    return data;
  }

  async syncPatternToCloud(pattern) {
    const { data, error } = await supabaseClient
      .from('workflow_patterns')
      .upsert({
        id: pattern.id,
        pattern_hash: pattern.pattern_hash,
        pattern_name: pattern.pattern_name,
        trigger_embedding: pattern.trigger_embedding,
        action_sequence: pattern.action_sequence,
        occurrence_count: pattern.occurrence_count,
        success_rate: pattern.success_rate,
        last_used: pattern.last_used,
        project_contexts: pattern.project_contexts,
        auto_apply: pattern.auto_apply
      }, {
        onConflict: 'id'
      });

    if (error) throw error;
    return data;
  }

  async getUnsyncedMemories() {
    const sql = `
      SELECT * FROM project_memories_cache
      WHERE synced_to_cloud = 0 OR synced_to_cloud IS NULL
      ORDER BY created_at
      LIMIT 100
    `;

    try {
      return await sqliteClient.db.all(sql);
    } catch (error) {
      logger.error('Failed to get unsynced memories', { 
        error: error.message 
      });
      return [];
    }
  }

  async getUnsyncedPatterns() {
    const sql = `
      SELECT * FROM workflow_patterns_cache
      WHERE synced_to_cloud = 0 OR synced_to_cloud IS NULL
      ORDER BY last_used
      LIMIT 50
    `;

    try {
      return await sqliteClient.db.all(sql);
    } catch (error) {
      logger.error('Failed to get unsynced patterns', { 
        error: error.message 
      });
      return [];
    }
  }

  async getLocalRecord(table, id) {
    const tableMap = {
      'project_memories': 'project_memories_cache',
      'workflow_patterns': 'workflow_patterns_cache'
    };

    const localTable = tableMap[table];
    if (!localTable) return null;

    const sql = `SELECT * FROM ${localTable} WHERE id = ?`;

    try {
      return await sqliteClient.db.get(sql, [id]);
    } catch (error) {
      logger.error('Failed to get local record', { 
        table, 
        id, 
        error: error.message 
      });
      return null;
    }
  }

  async insertLocalRecord(table, record) {
    if (table === 'project_memories') {
      await sqliteClient.storeMemory({
        ...record,
        embedding: record.embedding
      });
    } else if (table === 'workflow_patterns') {
      await sqliteClient.storePattern({
        ...record,
        trigger_embedding: record.trigger_embedding
      });
    }
  }

  async updateLocalRecord(table, record) {
    const tableMap = {
      'project_memories': 'project_memories_cache',
      'workflow_patterns': 'workflow_patterns_cache'
    };

    const localTable = tableMap[table];
    if (!localTable) return;

    // Build update query dynamically
    const fields = Object.keys(record).filter(k => k !== 'id');
    const sql = `
      UPDATE ${localTable}
      SET ${fields.map(f => `${f} = ?`).join(', ')}
      WHERE id = ?
    `;

    const values = fields.map(f => {
      const value = record[f];
      return typeof value === 'object' ? JSON.stringify(value) : value;
    });
    values.push(record.id);

    try {
      await sqliteClient.db.run(sql, values);
    } catch (error) {
      logger.error('Failed to update local record', { 
        table, 
        id: record.id, 
        error: error.message 
      });
    }
  }

  async deleteLocalRecord(table, id) {
    const tableMap = {
      'project_memories': 'project_memories_cache',
      'workflow_patterns': 'workflow_patterns_cache'
    };

    const localTable = tableMap[table];
    if (!localTable) return;

    const sql = `DELETE FROM ${localTable} WHERE id = ?`;

    try {
      await sqliteClient.db.run(sql, [id]);
    } catch (error) {
      logger.error('Failed to delete local record', { 
        table, 
        id, 
        error: error.message 
      });
    }
  }

  async resolveConflict(table, localRecord, remoteRecord) {
    this.syncMetrics.conflictsResolved++;
    
    const localTime = new Date(localRecord.updated_at || localRecord.created_at).getTime();
    const remoteTime = new Date(remoteRecord.updated_at || remoteRecord.created_at).getTime();
    
    if (this.conflictResolutionStrategy === 'local-wins-recent') {
      if (localTime > remoteTime) {
        // Push local to remote
        await this.pushToRemote(table, localRecord);
        logger.debug('Conflict resolved: local wins', { 
          table, 
          id: localRecord.id 
        });
      } else {
        // Update local with remote
        await this.updateLocalRecord(table, remoteRecord);
        logger.debug('Conflict resolved: remote wins', { 
          table, 
          id: remoteRecord.id 
        });
      }
    } else {
      // Remote always wins
      await this.updateLocalRecord(table, remoteRecord);
    }
  }

  async pushToRemote(table, record) {
    if (table === 'project_memories') {
      await this.syncMemoryToCloud(record);
    } else if (table === 'workflow_patterns') {
      await this.syncPatternToCloud(record);
    }
  }

  setupOfflineDetection() {
    // Check connection every 30 seconds
    setInterval(async () => {
      const wasOnline = this.isOnline;
      await this.checkConnection();
      
      if (!wasOnline && this.isOnline) {
        logger.info('Connection restored, syncing offline queue');
        await this.syncAll();
      } else if (wasOnline && !this.isOnline) {
        logger.warn('Connection lost, entering offline mode');
      }
    }, 30000);
  }

  startPeriodicSync() {
    // Sync every 5 minutes
    this.syncInterval = setInterval(() => {
      this.syncAll();
    }, config.sync?.intervalMs || 5 * 60 * 1000);
    
    // Initial sync after 5 seconds
    setTimeout(() => {
      this.syncAll();
    }, 5000);
  }

  trackSyncMetrics(success, duration) {
    this.syncMetrics.totalSyncs++;
    
    if (success) {
      this.syncMetrics.successfulSyncs++;
    } else {
      this.syncMetrics.failedSyncs++;
    }
    
    this.syncMetrics.syncTimes.push(duration);
    
    // Keep only last 100 times
    if (this.syncMetrics.syncTimes.length > 100) {
      this.syncMetrics.syncTimes.shift();
    }
    
    // Calculate average
    this.syncMetrics.avgSyncTime = 
      this.syncMetrics.syncTimes.reduce((a, b) => a + b, 0) / 
      this.syncMetrics.syncTimes.length;
  }

  async getMetrics() {
    const queueStats = await sqliteClient.getStats();
    
    return {
      ...this.syncMetrics,
      lastSyncTime: this.lastSyncTime,
      isOnline: this.isOnline,
      syncInProgress: this.syncInProgress,
      offlineQueueSize: this.offlineQueue.length,
      pendingSyncItems: queueStats.pendingSync,
      recentSyncTimes: this.syncMetrics.syncTimes.slice(-10)
    };
  }

  async stop() {
    // Clear intervals
    if (this.syncInterval) {
      clearInterval(this.syncInterval);
    }
    
    // Unsubscribe from realtime
    if (this.realtimeSubscription) {
      await this.realtimeSubscription.unsubscribe();
    }
    
    // Final sync
    await this.syncAll();
    
    logger.info('Sync Engine stopped');
  }
}

export default new SyncEngine();