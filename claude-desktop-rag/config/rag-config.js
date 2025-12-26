import dotenv from 'dotenv';
import { fileURLToPath } from 'url';
import { dirname, join } from 'path';

const __dirname = dirname(fileURLToPath(import.meta.url));
dotenv.config({ path: join(__dirname, '..', '.env') });

export const config = {
  // OpenAI Configuration
  openai: {
    apiKey: process.env.OPENAI_API_KEY,
    embeddingModel: process.env.EMBEDDING_MODEL || 'text-embedding-3-small',
    embeddingDimensions: parseInt(process.env.EMBEDDING_DIMENSIONS || '1536'),
    batchSize: parseInt(process.env.EMBEDDING_BATCH_SIZE || '100'),
    cacheTTL: parseInt(process.env.EMBEDDING_CACHE_TTL || '3600')
  },

  // Supabase Configuration
  supabase: {
    url: process.env.SUPABASE_URL,
    anonKey: process.env.SUPABASE_ANON_KEY,
    serviceRoleKey: process.env.SUPABASE_SERVICE_ROLE_KEY
  },

  // Project Configuration
  project: {
    id: process.env.PROJECT_ID || 'demestihas-mas',
    userId: process.env.USER_ID || 'default_user'
  },

  // User Configuration
  user: {
    id: process.env.USER_ID || 'default_user'
  },

  // Database Configuration
  database: {
    sqlitePath: process.env.SQLITE_DB_PATH || './data/local_memory.db',
    maxLocalItems: parseInt(process.env.MAX_LOCAL_ITEMS || '1000'),
    cacheTTLHours: parseInt(process.env.CACHE_TTL_HOURS || '24'),
    syncBatchSize: 50,
    syncIntervalMs: 30000 // 30 seconds
  },

  // RAG Configuration
  rag: {
    similarityThreshold: parseFloat(process.env.SIMILARITY_THRESHOLD || '0.70'),
    patternThreshold: parseFloat(process.env.PATTERN_THRESHOLD || '0.80'),
    patternMinOccurrences: parseInt(process.env.PATTERN_MIN_OCCURRENCES || '3'),
    patternTimeWindowDays: parseInt(process.env.PATTERN_TIME_WINDOW_DAYS || '7'),
    maxContextItems: parseInt(process.env.MAX_CONTEXT_ITEMS || '15'),
    contextBoostCurrentProject: parseFloat(process.env.CONTEXT_BOOST_CURRENT_PROJECT || '1.5'),
    contextBoostRecent: parseFloat(process.env.CONTEXT_BOOST_RECENT || '1.2'),
    retrievalTimeoutMs: parseInt(process.env.RETRIEVAL_TIMEOUT_MS || '1000')
  },

  // Performance Configuration
  performance: {
    parallelSearches: true,
    maxConcurrentEmbeddings: 5,
    retryAttempts: 3,
    retryDelayMs: 1000,
    pruneIntervalMs: 3600000, // 1 hour
    maxEmbeddingCacheSize: 1000
  },

  // Logging Configuration
  logging: {
    level: process.env.LOG_LEVEL || 'info',
    file: process.env.LOG_FILE || './logs/rag-system.log'
  }
};

// Validate required configuration
export function validateConfig() {
  const required = [
    ['openai.apiKey', config.openai.apiKey],
    ['supabase.url', config.supabase.url],
    ['supabase.anonKey', config.supabase.anonKey]
  ];

  const missing = required.filter(([name, value]) => !value);
  
  if (missing.length > 0) {
    const missingKeys = missing.map(([name]) => name).join(', ');
    throw new Error(`Missing required configuration: ${missingKeys}. Please check your .env file.`);
  }

  return true;
}