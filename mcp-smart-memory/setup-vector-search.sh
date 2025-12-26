#!/bin/bash

# Setup Vector Search Implementation
# This script guides you through setting up pgvector semantic search

set -e

echo "🚀 Smart Memory Vector Search Setup"
echo "===================================="
echo ""

# Check if .env exists
if [ ! -f .env ]; then
    echo "❌ .env file not found!"
    echo "Creating from template..."
    cp .env.example .env 2>/dev/null || {
        cat > .env << 'EOF'
# Supabase Configuration
SUPABASE_URL=your_supabase_project_url_here
SUPABASE_ANON_KEY=your_supabase_anon_key_here

# OpenAI Configuration (for embeddings)
OPENAI_API_KEY=your_openai_api_key_here

# Server Configuration
PORT=7777
NODE_ENV=development
EOF
    }
    echo "✅ Created .env file"
    echo ""
    echo "⚠️  IMPORTANT: Edit .env with your actual credentials:"
    echo "   - SUPABASE_URL: Your Supabase project URL"
    echo "   - SUPABASE_ANON_KEY: Your Supabase anon key"
    echo "   - OPENAI_API_KEY: Your OpenAI API key"
    echo ""
    echo "Press Enter after updating .env to continue..."
    read
fi

# Check if credentials are set
source .env
if [[ "$SUPABASE_URL" == "your_supabase_project_url_here" ]]; then
    echo "❌ Please update .env with real credentials first!"
    exit 1
fi

echo "✅ Environment configured"
echo ""

# Check Node.js
if ! command -v node &> /dev/null; then
    echo "❌ Node.js is not installed!"
    exit 1
fi

echo "✅ Node.js found: $(node --version)"
echo ""

# Install dependencies
echo "📦 Installing dependencies..."
npm install || {
    echo "❌ Failed to install dependencies"
    exit 1
}
echo "✅ Dependencies installed"
echo ""

# Show SQL migration instructions
echo "📋 NEXT STEP: Run SQL Migrations in Supabase"
echo "============================================"
echo ""
echo "1. Go to your Supabase project dashboard"
echo "2. Navigate to SQL Editor"
echo "3. Copy the contents of: supabase-pgvector-setup.sql"
echo "4. Paste and run in SQL Editor"
echo ""
echo "The SQL file is located at:"
echo "  $(pwd)/supabase-pgvector-setup.sql"
echo ""
echo "Press Enter after running SQL migrations to continue..."
read

# Test Supabase connection
echo "🔍 Testing Supabase connection..."
node -e "
const { createClient } = require('@supabase/supabase-js');
const supabase = createClient('$SUPABASE_URL', '$SUPABASE_ANON_KEY');

async function test() {
  try {
    const { data, error } = await supabase.rpc('test_pgvector');
    if (error) throw error;
    if (data === true) {
      console.log('✅ Supabase connected and pgvector enabled!');
      process.exit(0);
    } else {
      console.log('⚠️  pgvector test returned false');
      process.exit(1);
    }
  } catch (error) {
    console.error('❌ Connection failed:', error.message);
    console.log('Please ensure SQL migrations have been run');
    process.exit(1);
  }
}
test();
" || {
    echo ""
    echo "⚠️  Couldn't verify pgvector setup. Continuing anyway..."
    echo "   You can test manually later with: node test-vector-search.js"
}

echo ""
echo "🔄 Migrate existing memories? (y/n)"
read -n 1 -r
echo ""
if [[ $REPLY =~ ^[Yy]$ ]]; then
    echo "📊 Starting migration..."
    node migrate-to-vectors.js || {
        echo "⚠️  Migration had some issues. Check the output above."
    }
fi

echo ""
echo "🎯 Setup Complete!"
echo "=================="
echo ""
echo "Start the API server with:"
echo "  node memory-api-vector.js"
echo ""
echo "Or run in background:"
echo "  npm start"
echo ""
echo "Test the implementation:"
echo "  node test-vector-search.js"
echo ""
echo "📚 Full documentation:"
echo "  VECTOR_IMPLEMENTATION_GUIDE.md"
echo ""
echo "Happy semantic searching! 🚀"
