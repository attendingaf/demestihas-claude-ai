import { createClient } from '@supabase/supabase-js';
import winston from 'winston';
import { config } from '../../config/rag-config.js';

const logger = winston.createLogger({
  level: config.logging.level,
  format: winston.format.json(),
  transports: [
    new winston.transports.Console(),
    new winston.transports.File({ filename: config.logging.file })
  ]
});

class SupabaseClient {
  constructor() {
    this.client = null;
    this.initialized = false;
  }

  /**
   * Initialize Supabase client
   */
  async initialize() {
    if (this.initialized) return;

    try {
      this.client = createClient(
        config.supabase.url,
        config.supabase.serviceRoleKey || config.supabase.anonKey,
        {
          auth: {
            autoRefreshToken: true,
            persistSession: false
          }
        }
      );

      // Test connection
      const { error } = await this.client
        .from('project_memories')
        .select('count')
        .limit(1);

      if (error && error.code !== 'PGRST116') { // Table doesn't exist yet is OK
        throw error;
      }

      this.initialized = true;
      logger.info('Supabase client initialized successfully');
    } catch (error) {
      logger.error('Failed to initialize Supabase client', { error: error.message });
      throw error;
    }
  }

  /**
   * Store memory in Supabase
   */
  async storeMemory(memory) {
    await this.ensureInitialized();

    try {
      const { data, error } = await this.client
        .from('project_memories')
        .insert([memory])
        .select()
        .single();

      if (error) throw error;

      logger.debug('Memory stored in Supabase', { id: data.id });
      return data;
    } catch (error) {
      logger.error('Failed to store memory in Supabase', { error: error.message });
      throw error;
    }
  }

  /**
   * Store multiple memories
   */
  async storeMemories(memories) {
    await this.ensureInitialized();

    try {
      const { data, error } = await this.client
        .from('project_memories')
        .upsert(memories, { onConflict: 'id' })
        .select();

      if (error) throw error;

      logger.info('Memories stored in Supabase', { count: data.length });
      return data;
    } catch (error) {
      logger.error('Failed to store memories in Supabase', { error: error.message });
      throw error;
    }
  }

  /**
   * Search memories by vector similarity
   */
  async searchMemories(embedding, options = {}) {
    await this.ensureInitialized();

    const {
      limit = config.rag.maxContextItems,
      threshold = config.rag.similarityThreshold,
      projectId = config.project.id,
      filters = {}
    } = options;

    try {
      // Build the RPC call for vector similarity search
      let query = this.client.rpc('match_memories', {
        query_embedding: embedding,
        similarity_threshold: threshold,
        match_count: limit,
        filter_project_id: projectId
      });

      // Apply additional filters if provided
      if (filters.startDate) {
        query = query.gte('created_at', filters.startDate);
      }
      if (filters.endDate) {
        query = query.lte('created_at', filters.endDate);
      }
      if (filters.sessionId) {
        query = query.eq('session_id', filters.sessionId);
      }

      const { data, error } = await query;

      if (error) throw error;

      logger.debug('Memories searched in Supabase', { count: data?.length || 0 });
      return data || [];
    } catch (error) {
      logger.error('Failed to search memories in Supabase', { error: error.message });
      // Return empty array on error to allow fallback to local
      return [];
    }
  }

  /**
   * Store workflow pattern
   */
  async storePattern(pattern) {
    await this.ensureInitialized();

    try {
      const { data, error } = await this.client
        .from('workflow_patterns')
        .upsert([pattern], {
          onConflict: 'pattern_hash'
        })
        .select()
        .single();

      if (error) throw error;

      logger.debug('Pattern stored in Supabase', { id: data.id });
      return data;
    } catch (error) {
      logger.error('Failed to store pattern in Supabase', { error: error.message });
      throw error;
    }
  }

  /**
   * Search workflow patterns
   */
  async searchPatterns(embedding, options = {}) {
    await this.ensureInitialized();

    const {
      limit = 10,
      threshold = config.rag.patternThreshold,
      minOccurrences = config.rag.patternMinOccurrences
    } = options;

    try {
      const { data, error } = await this.client.rpc('match_patterns', {
        query_embedding: embedding,
        similarity_threshold: threshold,
        match_count: limit,
        min_occurrences: minOccurrences
      });

      if (error) throw error;

      logger.debug('Patterns searched in Supabase', { count: data?.length || 0 });
      return data || [];
    } catch (error) {
      logger.error('Failed to search patterns in Supabase', { error: error.message });
      return [];
    }
  }

  /**
   * Store knowledge artifact
   */
  async storeKnowledge(artifact) {
    await this.ensureInitialized();

    try {
      const { data, error } = await this.client
        .from('knowledge_artifacts')
        .insert([artifact])
        .select()
        .single();

      if (error) throw error;

      logger.debug('Knowledge artifact stored in Supabase', { id: data.id });
      return data;
    } catch (error) {
      logger.error('Failed to store knowledge artifact in Supabase', { error: error.message });
      throw error;
    }
  }

  /**
   * Search knowledge artifacts
   */
  async searchKnowledge(embedding, options = {}) {
    await this.ensureInitialized();

    const {
      limit = 10,
      threshold = config.rag.similarityThreshold,
      artifactType = null
    } = options;

    try {
      let query = this.client.rpc('match_knowledge', {
        query_embedding: embedding,
        similarity_threshold: threshold,
        match_count: limit
      });

      if (artifactType) {
        query = query.eq('artifact_type', artifactType);
      }

      const { data, error } = await query;

      if (error) throw error;

      logger.debug('Knowledge artifacts searched in Supabase', { count: data?.length || 0 });
      return data || [];
    } catch (error) {
      logger.error('Failed to search knowledge artifacts in Supabase', { error: error.message });
      return [];
    }
  }

  /**
   * Create RPC functions for vector similarity search
   */
  async createRPCFunctions() {
    await this.ensureInitialized();

    const functions = [
      {
        name: 'match_memories',
        definition: `
          CREATE OR REPLACE FUNCTION match_memories(
            query_embedding vector(1536),
            similarity_threshold float,
            match_count int,
            filter_project_id text DEFAULT NULL
          )
          RETURNS TABLE(
            id uuid,
            content text,
            similarity float,
            metadata jsonb,
            created_at timestamp,
            file_paths text[],
            tool_chain text[]
          )
          LANGUAGE plpgsql
          AS $$
          BEGIN
            RETURN QUERY
            SELECT 
              pm.id,
              pm.content,
              1 - (pm.embedding <=> query_embedding) as similarity,
              pm.metadata,
              pm.created_at,
              pm.file_paths,
              pm.tool_chain
            FROM project_memories pm
            WHERE 
              1 - (pm.embedding <=> query_embedding) > similarity_threshold
              AND (filter_project_id IS NULL OR pm.project_id = filter_project_id)
            ORDER BY pm.embedding <=> query_embedding
            LIMIT match_count;
          END;
          $$;
        `
      },
      {
        name: 'match_patterns',
        definition: `
          CREATE OR REPLACE FUNCTION match_patterns(
            query_embedding vector(1536),
            similarity_threshold float,
            match_count int,
            min_occurrences int DEFAULT 1
          )
          RETURNS TABLE(
            id uuid,
            pattern_name text,
            similarity float,
            action_sequence jsonb,
            occurrence_count int,
            success_rate float
          )
          LANGUAGE plpgsql
          AS $$
          BEGIN
            RETURN QUERY
            SELECT 
              wp.id,
              wp.pattern_name,
              1 - (wp.trigger_embedding <=> query_embedding) as similarity,
              wp.action_sequence,
              wp.occurrence_count,
              wp.success_rate
            FROM workflow_patterns wp
            WHERE 
              1 - (wp.trigger_embedding <=> query_embedding) > similarity_threshold
              AND wp.occurrence_count >= min_occurrences
            ORDER BY wp.trigger_embedding <=> query_embedding
            LIMIT match_count;
          END;
          $$;
        `
      },
      {
        name: 'match_knowledge',
        definition: `
          CREATE OR REPLACE FUNCTION match_knowledge(
            query_embedding vector(1536),
            similarity_threshold float,
            match_count int
          )
          RETURNS TABLE(
            id uuid,
            title text,
            content text,
            similarity float,
            artifact_type text,
            importance_score float
          )
          LANGUAGE plpgsql
          AS $$
          BEGIN
            RETURN QUERY
            SELECT 
              ka.id,
              ka.title,
              ka.content,
              1 - (ka.embedding <=> query_embedding) as similarity,
              ka.artifact_type,
              ka.importance_score
            FROM knowledge_artifacts ka
            WHERE 
              1 - (ka.embedding <=> query_embedding) > similarity_threshold
            ORDER BY ka.embedding <=> query_embedding
            LIMIT match_count;
          END;
          $$;
        `
      }
    ];

    for (const func of functions) {
      try {
        const { error } = await this.client.rpc('exec_sql', {
          sql: func.definition
        });

        if (error) {
          logger.warn(`Failed to create RPC function ${func.name}`, { error: error.message });
        } else {
          logger.info(`RPC function ${func.name} created successfully`);
        }
      } catch (error) {
        logger.warn(`Error creating RPC function ${func.name}`, { error: error.message });
      }
    }
  }

  /**
   * Ensure client is initialized
   */
  async ensureInitialized() {
    if (!this.initialized) {
      await this.initialize();
    }
  }

  /**
   * Get client statistics
   */
  async getStats() {
    await this.ensureInitialized();

    try {
      const [memories, patterns, knowledge] = await Promise.all([
        this.client.from('project_memories').select('count', { count: 'exact' }),
        this.client.from('workflow_patterns').select('count', { count: 'exact' }),
        this.client.from('knowledge_artifacts').select('count', { count: 'exact' })
      ]);

      return {
        memories: memories.count || 0,
        patterns: patterns.count || 0,
        knowledge: knowledge.count || 0
      };
    } catch (error) {
      logger.error('Failed to get Supabase stats', { error: error.message });
      return { memories: 0, patterns: 0, knowledge: 0 };
    }
  }
}

export default new SupabaseClient();