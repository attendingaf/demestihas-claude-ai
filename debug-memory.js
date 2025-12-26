#!/usr/bin/env node

// Debug script to find where memories are actually being stored
import { createClient } from '@supabase/supabase-js';
import sqlite3 from 'sqlite3';
import { open } from 'sqlite';
import dotenv from 'dotenv';
import path from 'path';
import { fileURLToPath } from 'url';

const __dirname = path.dirname(fileURLToPath(import.meta.url));
dotenv.config({ path: path.join(__dirname, 'claude-desktop-rag/.env') });

async function debugMemoryStorage() {
  console.log('=== MEMORY STORAGE DEBUG ===\n');
  
  // 1. Check Supabase tables
  console.log('1️⃣ CHECKING SUPABASE...\n');
  const supabase = createClient(
    process.env.SUPABASE_URL,
    process.env.SUPABASE_SERVICE_ROLE_KEY || process.env.SUPABASE_ANON_KEY
  );
  
  // Check project_memories
  try {
    const { count: pmCount, error: pmError } = await supabase
      .from('project_memories')
      .select('*', { count: 'exact', head: true });
    
    console.log(`project_memories: ${pmError ? 'ERROR - ' + pmError.message : pmCount + ' records'}`);
    
    // Get latest record
    const { data: pmLatest } = await supabase
      .from('project_memories')
      .select('id, content, created_at')
      .order('created_at', { ascending: false })
      .limit(1);
    
    if (pmLatest && pmLatest[0]) {
      console.log(`Latest: ${pmLatest[0].content?.substring(0, 50)}...`);
    }
  } catch (err) {
    console.error('project_memories error:', err.message);
  }
  
  // Check memories table
  try {
    const { count: mCount, error: mError } = await supabase
      .from('memories')
      .select('*', { count: 'exact', head: true });
    
    if (!mError) {
      console.log(`memories: ${mCount} records`);
    }
  } catch (err) {
    // Table might not exist
  }
  
  // Check knowledge_artifacts
  try {
    const { count: kaCount } = await supabase
      .from('knowledge_artifacts')
      .select('*', { count: 'exact', head: true });
    
    console.log(`knowledge_artifacts: ${kaCount} records`);
  } catch (err) {}
  
  // Check workflow_patterns
  try {
    const { count: wpCount } = await supabase
      .from('workflow_patterns')
      .select('*', { count: 'exact', head: true });
    
    console.log(`workflow_patterns: ${wpCount} records`);
  } catch (err) {}
  
  // 2. Check local SQLite databases
  console.log('\n2️⃣ CHECKING LOCAL SQLITE...\n');
  
  // Check MCP smart memory SQLite
  try {
    const mcpDb = await open({
      filename: path.join(__dirname, 'mcp-smart-memory/data/smart_memory.db'),
      driver: sqlite3.Database
    });
    
    const mcpCount = await mcpDb.get('SELECT COUNT(*) as count FROM memories');
    console.log(`MCP smart_memory.db: ${mcpCount.count} memories`);
    
    const latest = await mcpDb.get('SELECT * FROM memories ORDER BY timestamp DESC LIMIT 1');
    if (latest) {
      console.log(`Latest: ${latest.content?.substring(0, 50)}...`);
    }
    
    await mcpDb.close();
  } catch (err) {
    console.log('MCP SQLite:', err.message);
  }
  
  // Check RAG system SQLite
  try {
    const ragDb = await open({
      filename: path.join(__dirname, 'claude-desktop-rag/local_cache.db'),
      driver: sqlite3.Database
    });
    
    const tables = await ragDb.all("SELECT name FROM sqlite_master WHERE type='table'");
    console.log(`\nRAG local_cache.db tables: ${tables.map(t => t.name).join(', ')}`);
    
    for (const table of tables) {
      if (table.name.includes('memor') || table.name.includes('cache')) {
        const count = await ragDb.get(`SELECT COUNT(*) as count FROM ${table.name}`);
        console.log(`  ${table.name}: ${count.count} records`);
      }
    }
    
    await ragDb.close();
  } catch (err) {
    console.log('RAG SQLite:', err.message);
  }
  
  // 3. Test retrieval
  console.log('\n3️⃣ TESTING RETRIEVAL...\n');
  
  try {
    const response = await fetch('http://localhost:7778/context?q=cloud+memory+after+fix&limit=5');
    const data = await response.json();
    
    console.log(`API search returned: ${data.memories?.length || 0} memories`);
    if (data.memories && data.memories.length > 0) {
      console.log('First result:', data.memories[0].content?.substring(0, 100));
    }
  } catch (err) {
    console.log('API retrieval error:', err.message);
  }
  
  // 4. Check for the specific memory we just stored
  console.log('\n4️⃣ LOOKING FOR RECENT STORE...\n');
  const testId = '5738ae36-9106-4d7f-90fe-314bfedc06f2';
  
  // Check Supabase
  try {
    const { data: specific } = await supabase
      .from('project_memories')
      .select('*')
      .eq('id', testId);
    
    if (specific && specific.length > 0) {
      console.log('✅ Found in Supabase project_memories!');
    } else {
      console.log('❌ Not in Supabase project_memories');
    }
  } catch (err) {}
  
  // Check local
  try {
    const mcpDb = await open({
      filename: path.join(__dirname, 'mcp-smart-memory/data/smart_memory.db'),
      driver: sqlite3.Database
    });
    
    const local = await mcpDb.get('SELECT * FROM memories WHERE id = ?', testId);
    if (local) {
      console.log('✅ Found in local SQLite!');
    } else {
      console.log('❌ Not in local SQLite');
    }
    
    await mcpDb.close();
  } catch (err) {}
  
  console.log('\n=== DIAGNOSIS ===');
  console.log('Memories are likely being stored in local SQLite only.');
  console.log('The RAG adapter may not be pushing to Supabase correctly.');
  console.log('Check if embedding generation is failing (OpenAI API key issue).');
}

debugMemoryStorage();
