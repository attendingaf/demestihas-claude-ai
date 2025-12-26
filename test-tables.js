#!/usr/bin/env node

// Test script to verify Supabase table structure and fix if needed
import { createClient } from '@supabase/supabase-js';
import dotenv from 'dotenv';
import path from 'path';
import { fileURLToPath } from 'url';

const __dirname = path.dirname(fileURLToPath(import.meta.url));
dotenv.config({ path: path.join(__dirname, 'claude-desktop-rag/.env') });

async function testAndFixSupabase() {
  console.log('=== TESTING EXISTING TABLES ===\n');
  
  const supabase = createClient(
    process.env.SUPABASE_URL,
    process.env.SUPABASE_SERVICE_ROLE_KEY || process.env.SUPABASE_ANON_KEY
  );
  
  // Test 1: Check project_memories table
  console.log('1️⃣ Testing project_memories table...');
  try {
    const { data, error } = await supabase
      .from('project_memories')
      .select('*')
      .limit(1);
    
    if (error) {
      console.error('❌ Error accessing project_memories:', error.message);
      console.log('\nTrying to add missing columns...');
      
      // Try to add embedding column if missing
      const { error: alterError } = await supabase.rpc('execute_sql', {
        query: `
          ALTER TABLE project_memories 
          ADD COLUMN IF NOT EXISTS embedding vector(1536);
        `
      });
      
      if (alterError) {
        console.log('Note: Cannot modify table via API. Please add embedding column manually.');
      }
    } else {
      console.log('✅ project_memories table accessible');
      console.log('   Columns:', data[0] ? Object.keys(data[0]) : 'Empty table');
    }
  } catch (err) {
    console.error('Error:', err);
  }
  
  // Test 2: Insert test memory
  console.log('\n2️⃣ Inserting test memory...');
  try {
    const testData = {
      content: `Supabase test at ${new Date().toISOString()}`,
      interaction_type: 'test',
      success_score: 1.0,
      project_id: 'mcp-smart-memory',
      user_id: 'test-user',
      metadata: { test: true }
    };
    
    const { data, error } = await supabase
      .from('project_memories')
      .insert([testData])
      .select();
    
    if (error) {
      console.error('❌ Insert error:', error.message);
      console.log('\nSuggested fix: Check if these columns exist:');
      console.log('- content (text)');
      console.log('- interaction_type (text)');
      console.log('- success_score (float)');
      console.log('- project_id (text)');
      console.log('- user_id (text)');
      console.log('- metadata (jsonb)');
    } else {
      console.log('✅ Test memory inserted:', data[0].id);
    }
  } catch (err) {
    console.error('Error:', err);
  }
  
  // Test 3: Count total memories
  console.log('\n3️⃣ Counting memories...');
  try {
    const { count, error } = await supabase
      .from('project_memories')
      .select('*', { count: 'exact', head: true });
    
    if (error) {
      console.error('❌ Count error:', error.message);
    } else {
      console.log(`✅ Total memories: ${count}`);
    }
  } catch (err) {
    console.error('Error:', err);
  }
  
  // Test 4: Try to use memories table as fallback
  console.log('\n4️⃣ Testing memories table (fallback)...');
  try {
    const { error: checkError } = await supabase
      .from('memories')
      .select('count', { count: 'exact', head: true });
    
    if (checkError) {
      console.log('⚠️ memories table not found (creating would help)');
    } else {
      console.log('✅ memories table exists');
    }
  } catch (err) {
    console.log('No memories table');
  }
  
  // Test workflow_patterns table
  console.log('\n5️⃣ Testing workflow_patterns table...');
  try {
    const { count, error } = await supabase
      .from('workflow_patterns')
      .select('*', { count: 'exact', head: true });
    
    if (!error) {
      console.log(`✅ workflow_patterns table: ${count} patterns`);
    }
  } catch (err) {
    console.error('workflow_patterns error:', err.message);
  }
  
  console.log('\n=== RECOMMENDATIONS ===');
  console.log('1. Add embedding column to project_memories if missing:');
  console.log('   ALTER TABLE project_memories ADD COLUMN embedding vector(1536);');
  console.log('\n2. Or create a simple memories table as alias:');
  console.log('   CREATE OR REPLACE VIEW memories AS SELECT * FROM project_memories;');
}

testAndFixSupabase();
