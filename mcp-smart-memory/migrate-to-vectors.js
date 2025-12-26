import { config } from 'dotenv';
import { createClient } from '@supabase/supabase-js';
import OpenAI from 'openai';
import path from 'path';
import { fileURLToPath } from 'url';
import sqlite3 from 'sqlite3';
import { open } from 'sqlite';

const __dirname = path.dirname(fileURLToPath(import.meta.url));
config({ path: path.join(__dirname, '.env') });

class VectorMigration {
  constructor() {
    // Check for required environment variables
    if (!process.env.SUPABASE_URL || !process.env.SUPABASE_ANON_KEY) {
      console.error('❌ Supabase credentials not found in .env file');
      console.error('Please set SUPABASE_URL and SUPABASE_ANON_KEY');
      process.exit(1);
    }

    if (!process.env.OPENAI_API_KEY) {
      console.error('❌ OpenAI API key not found in .env file');
      console.error('Please set OPENAI_API_KEY');
      process.exit(1);
    }

    this.supabase = createClient(
      process.env.SUPABASE_URL,
      process.env.SUPABASE_ANON_KEY
    );

    this.openai = new OpenAI({
      apiKey: process.env.OPENAI_API_KEY
    });

    this.db = null;
  }

  async initialize() {
    // Open local SQLite database
    this.db = await open({
      filename: path.join(__dirname, 'data', 'smart_memory.db'),
      driver: sqlite3.Database
    });

    console.log('✅ Connected to local SQLite database');
  }

  async checkSupabaseSetup() {
    console.log('🔍 Checking Supabase setup...');

    try {
      // Test if pgvector is enabled
      const { data, error } = await this.supabase
        .rpc('test_pgvector');

      if (error) {
        console.error('❌ pgvector not properly set up:', error.message);
        console.log('\nPlease run the following SQL in your Supabase SQL editor:');
        console.log('----------------------------------------');
        console.log('CREATE EXTENSION IF NOT EXISTS vector;');
        console.log('----------------------------------------');
        return false;
      }

      if (data === true) {
        console.log('✅ pgvector extension is enabled');
        return true;
      } else {
        console.log('⚠️  pgvector test returned false');
        return false;
      }
    } catch (error) {
      console.error('❌ Failed to check Supabase setup:', error);
      return false;
    }
  }

  async createSupabaseTable() {
    console.log('📊 Ensuring Supabase table exists...');

    // Note: This would typically be done via Supabase dashboard
    // We'll check if we can query the table
    try {
      const { error } = await this.supabase
        .from('memories')
        .select('id')
        .limit(1);

      if (error) {
        console.error('⚠️  Memories table might not exist:', error.message);
        console.log('Please create it using the SQL in supabase-pgvector-setup.sql');
        return false;
      }

      console.log('✅ Memories table exists in Supabase');
      return true;
    } catch (error) {
      console.error('❌ Failed to check table:', error);
      return false;
    }
  }

  async getLocalMemories() {
    console.log('📚 Fetching local memories...');

    const memories = await this.db.all(`
      SELECT id, content, type, category, importance, metadata, timestamp
      FROM memories
      ORDER BY timestamp DESC
    `);

    console.log(`✅ Found ${memories.length} local memories`);
    return memories;
  }

  async getSupabaseMemoriesWithoutEmbeddings() {
    console.log('🔍 Checking Supabase for memories without embeddings...');

    const { data: memories, error } = await this.supabase
      .from('memories')
      .select('id, content')
      .is('embedding', null)
      .limit(1000);

    if (error) {
      console.error('Failed to fetch memories:', error);
      return [];
    }

    console.log(`Found ${memories?.length || 0} memories without embeddings in Supabase`);
    return memories || [];
  }

  async generateEmbedding(text) {
    try {
      const response = await this.openai.embeddings.create({
        model: 'text-embedding-3-small',
        input: text.substring(0, 8000), // Respect token limits
        dimensions: 1536
      });
      return response.data[0].embedding;
    } catch (error) {
      console.error(`Failed to generate embedding:`, error.message);
      return null;
    }
  }

  async syncLocalToSupabase() {
    console.log('\n🚀 Starting local to Supabase sync...');

    const localMemories = await this.getLocalMemories();

    if (localMemories.length === 0) {
      console.log('No local memories to sync');
      return;
    }

    console.log(`Processing ${localMemories.length} memories...`);

    let successCount = 0;
    let errorCount = 0;

    // Process in batches of 5
    for (let i = 0; i < localMemories.length; i += 5) {
      const batch = localMemories.slice(i, i + 5);

      const updates = await Promise.all(
        batch.map(async (memory) => {
          try {
            // Generate embedding
            const embedding = await this.generateEmbedding(memory.content);

            if (!embedding) {
              console.error(`⚠️  Skipping ${memory.id} - no embedding generated`);
              errorCount++;
              return null;
            }

            // Parse metadata if it's a string
            let metadata = memory.metadata;
            if (typeof metadata === 'string') {
              try {
                metadata = JSON.parse(metadata);
              } catch {
                metadata = {};
              }
            }

            return {
              id: memory.id,
              content: memory.content,
              embedding,
              metadata,
              category: memory.category || 'general',
              importance: memory.importance || 'medium',
              timestamp: memory.timestamp || Date.now(),
              type: memory.type || 'note'
            };
          } catch (error) {
            console.error(`❌ Failed to process ${memory.id}:`, error.message);
            errorCount++;
            return null;
          }
        })
      );

      // Filter out failed ones
      const validUpdates = updates.filter(u => u !== null);

      // Batch upsert to Supabase
      if (validUpdates.length > 0) {
        const { error } = await this.supabase
          .from('memories')
          .upsert(validUpdates);

        if (error) {
          console.error('❌ Batch upsert failed:', error);
          errorCount += validUpdates.length;
        } else {
          successCount += validUpdates.length;
        }
      }

      console.log(`Progress: ${i + batch.length}/${localMemories.length} (${successCount} success, ${errorCount} errors)`);

      // Small delay to avoid rate limiting
      await new Promise(resolve => setTimeout(resolve, 500));
    }

    console.log('\n📊 Sync Summary:');
    console.log(`✅ Successfully synced: ${successCount} memories`);
    console.log(`❌ Failed: ${errorCount} memories`);
  }

  async updateExistingSupabaseMemories() {
    console.log('\n🔄 Updating existing Supabase memories with embeddings...');

    const memories = await this.getSupabaseMemoriesWithoutEmbeddings();

    if (memories.length === 0) {
      console.log('✅ All Supabase memories already have embeddings');
      return;
    }

    console.log(`Processing ${memories.length} memories...`);

    let successCount = 0;
    let errorCount = 0;

    // Process in batches of 5
    for (let i = 0; i < memories.length; i += 5) {
      const batch = memories.slice(i, i + 5);

      for (const memory of batch) {
        try {
          const embedding = await this.generateEmbedding(memory.content);

          if (!embedding) {
            console.error(`⚠️  Skipping ${memory.id} - no embedding generated`);
            errorCount++;
            continue;
          }

          const { error } = await this.supabase
            .from('memories')
            .update({ embedding })
            .eq('id', memory.id);

          if (error) {
            console.error(`❌ Failed to update ${memory.id}:`, error.message);
            errorCount++;
          } else {
            successCount++;
          }
        } catch (error) {
          console.error(`❌ Error processing ${memory.id}:`, error.message);
          errorCount++;
        }
      }

      console.log(`Progress: ${i + batch.length}/${memories.length} (${successCount} success, ${errorCount} errors)`);

      // Small delay to avoid rate limiting
      await new Promise(resolve => setTimeout(resolve, 500));
    }

    console.log('\n📊 Update Summary:');
    console.log(`✅ Successfully updated: ${successCount} memories`);
    console.log(`❌ Failed: ${errorCount} memories`);
  }

  async testVectorSearch() {
    console.log('\n🧪 Testing vector search...');

    const testQuery = "medical compliance documentation";
    console.log(`Test query: "${testQuery}"`);

    try {
      // Generate query embedding
      const queryEmbedding = await this.generateEmbedding(testQuery);

      if (!queryEmbedding) {
        console.error('❌ Failed to generate test query embedding');
        return;
      }

      // Test semantic search
      const { data, error } = await this.supabase
        .rpc('search_memories_semantic', {
          query_embedding: queryEmbedding,
          match_count: 3,
          similarity_threshold: 0.5
        });

      if (error) {
        console.error('❌ Vector search test failed:', error);
        return;
      }

      if (data && data.length > 0) {
        console.log(`✅ Vector search working! Found ${data.length} results:`);
        data.forEach((result, i) => {
          console.log(`  ${i + 1}. Similarity: ${result.similarity.toFixed(3)} - ${result.content.substring(0, 50)}...`);
        });
      } else {
        console.log('⚠️  Vector search returned no results (this might be normal if no similar content exists)');
      }
    } catch (error) {
      console.error('❌ Test failed:', error);
    }
  }

  async run() {
    console.log('🚀 Starting Vector Migration Process\n');

    try {
      await this.initialize();

      // Check Supabase setup
      const pgvectorReady = await this.checkSupabaseSetup();
      if (!pgvectorReady) {
        console.log('\n⚠️  Please set up pgvector first using the SQL in supabase-pgvector-setup.sql');
        return;
      }

      // Ensure table exists
      const tableReady = await this.createSupabaseTable();
      if (!tableReady) {
        console.log('\n⚠️  Please create the memories table first');
        return;
      }

      // Sync local memories to Supabase
      await this.syncLocalToSupabase();

      // Update any Supabase memories without embeddings
      await this.updateExistingSupabaseMemories();

      // Test the vector search
      await this.testVectorSearch();

      console.log('\n✅ Migration complete!');
      console.log('\nNext steps:');
      console.log('1. Update your memory-api.js to use memory-api-vector.js');
      console.log('2. Update simple-memory-store.js to use simple-memory-store-vector.js');
      console.log('3. Test the new endpoints with: node test-vector-search.js');

    } catch (error) {
      console.error('\n❌ Migration failed:', error);
    } finally {
      if (this.db) {
        await this.db.close();
      }
    }
  }
}

// Run migration if called directly
if (import.meta.url === `file://${process.argv[1]}`) {
  const migration = new VectorMigration();
  migration.run();
}

export default VectorMigration;
