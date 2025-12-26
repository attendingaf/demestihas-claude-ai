#!/usr/bin/env node

// Simple test to see where the 48+ memories actually are
import sqlite3 from 'sqlite3';
import { open } from 'sqlite';
import path from 'path';
import { fileURLToPath } from 'url';

const __dirname = path.dirname(fileURLToPath(import.meta.url));

async function findAllMemories() {
  console.log('=== FINDING ALL MEMORIES ===\n');
  
  // Check the MCP SQLite database
  try {
    const db = await open({
      filename: path.join(__dirname, 'mcp-smart-memory/data/smart_memory.db'),
      driver: sqlite3.Database
    });
    
    const count = await db.get('SELECT COUNT(*) as total FROM memories');
    console.log(`✅ LOCAL SQLITE HAS: ${count.total} memories\n`);
    
    if (count.total > 0) {
      console.log('Recent memories:');
      const recent = await db.all('SELECT content, type, timestamp FROM memories ORDER BY timestamp DESC LIMIT 5');
      
      recent.forEach((mem, i) => {
        const date = new Date(parseInt(mem.timestamp));
        console.log(`${i + 1}. [${mem.type}] ${mem.content.substring(0, 60)}...`);
        console.log(`   Created: ${date.toLocaleString()}\n`);
      });
      
      // Check for the test memory we just stored
      const testMem = await db.get("SELECT * FROM memories WHERE content LIKE '%cloud memory after fix%'");
      if (testMem) {
        console.log('✅ Found "First cloud memory after fix" in local SQLite!');
        console.log(`   ID: ${testMem.id}`);
      }
    }
    
    await db.close();
  } catch (err) {
    console.error('Error reading SQLite:', err);
  }
}

findAllMemories();
