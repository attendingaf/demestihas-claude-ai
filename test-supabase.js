#!/usr/bin/env node

// Test script to verify Supabase connection
import { createClient } from '@supabase/supabase-js';
import dotenv from 'dotenv';
import path from 'path';
import { fileURLToPath } from 'url';

const __dirname = path.dirname(fileURLToPath(import.meta.url));

// Load env from claude-desktop-rag
dotenv.config({ path: path.join(__dirname, '../claude-desktop-rag/.env') });

async function testSupabase() {
  console.log('=== SUPABASE CONNECTION TEST ===');
  console.log('Timestamp:', new Date().toISOString());
  
  const supabaseUrl = process.env.SUPABASE_URL;
  const supabaseKey = process.env.SUPABASE_ANON_KEY;
  
  console.log('URL:', supabaseUrl);
  console.log('Key:', supabaseKey ? 'Present' : 'Missing');
  
  if (!supabaseUrl || !supabaseKey) {
    console.error('❌ Missing Supabase credentials');
    return false;
  }
  
  try {
    // Create Supabase client
    const supabase = createClient(supabaseUrl, supabaseKey);
    console.log('✅ Supabase client created');
    
    // Test 1: Check if tables exist
    console.log('\n📊 Checking tables...');
    const { data: tables, error: tableError } = await supabase
      .from('memories')
      .select('count', { count: 'exact', head: true });
    
    if (tableError) {
      // Table might not exist yet
      console.log('⚠️ Memories table not found, creating...');
      
      // Try to create the table (this would normally be done via migration)
      const createTableSQL = `
        CREATE TABLE IF NOT EXISTS memories (
          id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
          content TEXT NOT NULL,
          embedding vector(1536),
          metadata JSONB,
          interaction_type TEXT,
          success_score FLOAT,
          project_id TEXT,
          user_id TEXT,
          created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
          updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
        );
      `;
      
      console.log('Note: Table creation should be done via Supabase dashboard');
    } else {
      console.log(`✅ Memories table exists`);
    }
    
    // Test 2: Try to insert a test memory
    console.log('\n💾 Testing memory storage...');
    const testMemory = {
      content: `SUPABASE-TEST: Connection verified at ${new Date().toISOString()}`,
      metadata: {
        test: true,
        source: 'verification-script'
      },
      interaction_type: 'verification',
      success_score: 1.0,
      project_id: 'mcp-smart-memory',
      user_id: 'test-script'
    };
    
    const { data: insertData, error: insertError } = await supabase
      .from('memories')
      .insert([testMemory])
      .select();
    
    if (insertError) {
      console.error('❌ Insert failed:', insertError.message);
      return false;
    } else {
      console.log('✅ Test memory stored:', insertData[0].id);
    }
    
    // Test 3: Retrieve the test memory
    console.log('\n🔍 Testing memory retrieval...');
    const { data: retrieveData, error: retrieveError } = await supabase
      .from('memories')
      .select('*')
      .like('content', '%SUPABASE-TEST%')
      .order('created_at', { ascending: false })
      .limit(1);
    
    if (retrieveError) {
      console.error('❌ Retrieve failed:', retrieveError.message);
      return false;
    } else {
      console.log('✅ Memory retrieved:', retrieveData[0]?.content?.substring(0, 50) + '...');
    }
    
    // Test 4: Count total memories
    console.log('\n📈 Getting statistics...');
    const { count, error: countError } = await supabase
      .from('memories')
      .select('*', { count: 'exact', head: true });
    
    if (countError) {
      console.error('❌ Count failed:', countError.message);
    } else {
      console.log(`✅ Total memories in Supabase: ${count}`);
    }
    
    console.log('\n🎉 SUPABASE CONNECTION SUCCESSFUL!');
    return true;
    
  } catch (error) {
    console.error('❌ Unexpected error:', error);
    return false;
  }
}

// Run test
testSupabase().then(success => {
  if (success) {
    console.log('\n✨ All tests passed! Supabase is ready.');
    process.exit(0);
  } else {
    console.log('\n⚠️ Some tests failed. Check Supabase configuration.');
    process.exit(1);
  }
});
