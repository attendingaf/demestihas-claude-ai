#!/usr/bin/env node

import { config } from 'dotenv';
import path from 'path';
import { fileURLToPath } from 'url';
import fs from 'fs/promises';

const __dirname = path.dirname(fileURLToPath(import.meta.url));
config({ path: path.join(__dirname, '.env') });

// Color codes
const colors = {
  reset: '\x1b[0m',
  green: '\x1b[32m',
  red: '\x1b[31m',
  yellow: '\x1b[33m',
  blue: '\x1b[34m',
  cyan: '\x1b[36m'
};

function log(message, color = 'reset') {
  console.log(`${colors[color]}${message}${colors.reset}`);
}

async function checkFile(filename, description) {
  try {
    await fs.access(path.join(__dirname, filename));
    log(`✅ ${description}: ${filename}`, 'green');
    return true;
  } catch {
    log(`❌ ${description}: ${filename} - NOT FOUND`, 'red');
    return false;
  }
}

async function checkEnvVar(varName, description) {
  const value = process.env[varName];
  if (value && !value.includes('your_') && !value.includes('_here')) {
    log(`✅ ${description}: Configured`, 'green');
    return true;
  } else {
    log(`❌ ${description}: Not configured`, 'red');
    return false;
  }
}

async function main() {
  log('\n🔍 Vector Search Implementation Verification', 'cyan');
  log('=========================================\n', 'cyan');

  let allGood = true;

  // Check required files
  log('📁 Checking Required Files:', 'blue');
  allGood &= await checkFile('supabase-pgvector-setup.sql', 'SQL Migrations');
  allGood &= await checkFile('simple-memory-store-vector.js', 'Vector Memory Store');
  allGood &= await checkFile('memory-api-vector.js', 'Vector API Server');
  allGood &= await checkFile('migrate-to-vectors.js', 'Migration Script');
  allGood &= await checkFile('test-vector-search.js', 'Test Suite');
  allGood &= await checkFile('.env', 'Environment Config');

  // Check environment variables
  log('\n🔑 Checking Environment Variables:', 'blue');
  const envOk =
    await checkEnvVar('SUPABASE_URL', 'Supabase URL') &
    await checkEnvVar('SUPABASE_ANON_KEY', 'Supabase Key') &
    await checkEnvVar('OPENAI_API_KEY', 'OpenAI API Key');

  allGood &= envOk;

  // Check Node modules
  log('\n📦 Checking Dependencies:', 'blue');
  try {
    await fs.access(path.join(__dirname, 'node_modules', '@supabase', 'supabase-js'));
    log('✅ Supabase Client: Installed', 'green');
  } catch {
    log('❌ Supabase Client: Not installed', 'red');
    log('   Run: npm install @supabase/supabase-js', 'yellow');
    allGood = false;
  }

  try {
    await fs.access(path.join(__dirname, 'node_modules', 'openai'));
    log('✅ OpenAI SDK: Installed', 'green');
  } catch {
    log('❌ OpenAI SDK: Not installed', 'red');
    log('   Run: npm install openai', 'yellow');
    allGood = false;
  }

  // Summary
  log('\n📊 Summary:', 'blue');
  if (allGood) {
    log('✅ All components are in place!', 'green');
    log('\n🚀 Next Steps:', 'cyan');
    log('1. Run SQL migrations in Supabase dashboard', 'yellow');
    log('2. Start the API: node memory-api-vector.js', 'yellow');
    log('3. Migrate data: node migrate-to-vectors.js', 'yellow');
    log('4. Run tests: node test-vector-search.js', 'yellow');
  } else {
    log('⚠️  Some components are missing or not configured', 'red');
    log('\n📋 To Do:', 'cyan');

    if (!envOk) {
      log('1. Configure .env with your actual credentials', 'yellow');
    }

    log('2. Run: npm install', 'yellow');
    log('3. Follow setup guide: VECTOR_IMPLEMENTATION_GUIDE.md', 'yellow');
  }

  log('\n📚 Documentation: VECTOR_IMPLEMENTATION_GUIDE.md', 'blue');
}

main().catch(console.error);
