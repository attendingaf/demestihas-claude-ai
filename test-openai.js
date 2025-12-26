#!/usr/bin/env node

// Test OpenAI API key
import dotenv from 'dotenv';
import path from 'path';
import { fileURLToPath } from 'url';

const __dirname = path.dirname(fileURLToPath(import.meta.url));
dotenv.config({ path: path.join(__dirname, 'claude-desktop-rag/.env') });

async function testOpenAI() {
  console.log('=== TESTING OPENAI API ===\n');
  
  const apiKey = process.env.OPENAI_API_KEY;
  console.log('API Key present:', apiKey ? 'Yes' : 'No');
  console.log('Key prefix:', apiKey?.substring(0, 10) + '...');
  
  if (!apiKey) {
    console.log('❌ No OpenAI API key found');
    return;
  }
  
  try {
    // Test the key with a simple embedding request
    const response = await fetch('https://api.openai.com/v1/embeddings', {
      method: 'POST',
      headers: {
        'Authorization': `Bearer ${apiKey}`,
        'Content-Type': 'application/json'
      },
      body: JSON.stringify({
        model: 'text-embedding-3-small',
        input: 'Test embedding generation'
      })
    });
    
    const data = await response.json();
    
    if (response.ok) {
      console.log('✅ OpenAI API key is valid!');
      console.log('Embedding dimensions:', data.data[0].embedding.length);
    } else {
      console.log('❌ OpenAI API error:', data.error?.message || 'Unknown error');
      console.log('\nThis is why embeddings aren\'t being generated!');
      console.log('Without embeddings, memories can\'t sync to Supabase.');
    }
  } catch (err) {
    console.error('❌ Failed to test OpenAI:', err.message);
  }
  
  console.log('\n=== SOLUTION ===');
  console.log('Your memories ARE being stored locally (SQLite).');
  console.log('To enable Supabase sync, you need:');
  console.log('1. Valid OpenAI API key for embeddings');
  console.log('2. RPC functions in Supabase for vector search');
  console.log('3. Or just use local storage (working fine!)');
}

testOpenAI();
