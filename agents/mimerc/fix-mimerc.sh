#!/bin/bash
# Fix script for MiMerc database and configuration issues
# Run from: /Users/menedemestihas/Projects/demestihas-ai/agents/mimerc/

echo "🔧 MiMerc Fix Script Starting..."

# Step 1: Create correct PostgresSaver schema
cat > init-tables.sql << 'EOF'
-- LangGraph PostgresSaver Schema (Corrected Version)
-- Based on actual error messages from PostgresSaver

-- Drop existing tables if they exist (for clean restart)
DROP TABLE IF EXISTS checkpoint_writes CASCADE;
DROP TABLE IF EXISTS checkpoint_blobs CASCADE;
DROP TABLE IF EXISTS checkpoints CASCADE;

-- Main checkpoints table with correct columns
CREATE TABLE IF NOT EXISTS checkpoints (
    thread_id TEXT NOT NULL,
    checkpoint_ns TEXT NOT NULL DEFAULT '',
    checkpoint_id TEXT NOT NULL,
    parent_checkpoint_id TEXT,
    type TEXT,
    checkpoint JSONB NOT NULL,
    metadata JSONB DEFAULT '{}',
    created_at TIMESTAMPTZ DEFAULT NOW(),
    PRIMARY KEY (thread_id, checkpoint_ns, checkpoint_id)
);

-- Checkpoint blobs for channel data
CREATE TABLE IF NOT EXISTS checkpoint_blobs (
    thread_id TEXT NOT NULL,
    checkpoint_ns TEXT NOT NULL DEFAULT '',
    channel TEXT NOT NULL,
    version TEXT NOT NULL,
    type TEXT NOT NULL,
    blob BYTEA,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    PRIMARY KEY (thread_id, checkpoint_ns, channel, version)
);

-- Checkpoint writes with task_path column
CREATE TABLE IF NOT EXISTS checkpoint_writes (
    thread_id TEXT NOT NULL,
    checkpoint_ns TEXT NOT NULL DEFAULT '',
    checkpoint_id TEXT NOT NULL,
    task_id TEXT NOT NULL,
    task_path TEXT,  -- This column was missing!
    idx INTEGER NOT NULL,
    channel TEXT NOT NULL,
    type TEXT,
    blob BYTEA,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    PRIMARY KEY (thread_id, checkpoint_ns, checkpoint_id, task_id, idx)
);

-- Create indexes for performance
CREATE INDEX IF NOT EXISTS idx_checkpoints_thread_id 
    ON checkpoints(thread_id);
CREATE INDEX IF NOT EXISTS idx_checkpoints_created_at 
    ON checkpoints(created_at);
CREATE INDEX IF NOT EXISTS idx_checkpoint_blobs_thread 
    ON checkpoint_blobs(thread_id, checkpoint_ns);
CREATE INDEX IF NOT EXISTS idx_checkpoint_writes_thread 
    ON checkpoint_writes(thread_id, checkpoint_ns, checkpoint_id);

-- Grant permissions to mimerc user
GRANT ALL PRIVILEGES ON ALL TABLES IN SCHEMA public TO mimerc;
GRANT ALL PRIVILEGES ON ALL SEQUENCES IN SCHEMA public TO mimerc;

-- Success message
DO $$
BEGIN
    RAISE NOTICE 'PostgresSaver tables created successfully with correct schema';
END $$;
EOF

echo "✅ Step 1: Created correct SQL schema"

# Step 2: Create proper .env file
cat > .env << 'EOF'
# MiMerc Environment Variables
# IMPORTANT: Replace the OpenAI key with your actual key!

# OpenAI Configuration
OPENAI_API_KEY=sk-YOUR_ACTUAL_OPENAI_API_KEY_HERE

# PostgreSQL Configuration
POSTGRES_USER=mimerc
POSTGRES_PASSWORD=mimerc_secure_password
POSTGRES_DB=mimerc_db
POSTGRES_HOST=mimerc-postgres
POSTGRES_PORT=5432

# Connection string for PostgresSaver
PG_CONNINFO=postgresql://mimerc:mimerc_secure_password@mimerc-postgres:5432/mimerc_db

# Agent Configuration
AGENT_PORT=8000
LOG_LEVEL=INFO
EOF

echo "⚠️  Step 2: Created .env template - YOU MUST ADD YOUR OPENAI API KEY!"

# Step 3: Update docker-compose to mount init script
cat > docker-compose.yml << 'EOF'
version: '3.8'

services:
  mimerc-postgres:
    image: postgres:16-alpine
    container_name: mimerc-postgres
    environment:
      POSTGRES_USER: mimerc
      POSTGRES_PASSWORD: ${POSTGRES_PASSWORD:-mimerc_secure_password}
      POSTGRES_DB: mimerc_db
    volumes:
      - mimerc_postgres_data:/var/lib/postgresql/data
      - ./init-tables.sql:/docker-entrypoint-initdb.d/01-init-tables.sql
    ports:
      - "5433:5432"
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U mimerc -d mimerc_db"]
      interval: 5s
      timeout: 3s
      retries: 5
    networks:
      - mimerc-network

  mimerc-agent:
    build:
      context: .
      dockerfile: Dockerfile
    container_name: mimerc-agent
    env_file:
      - .env
    ports:
      - "8002:8000"
    depends_on:
      mimerc-postgres:
        condition: service_healthy
    networks:
      - mimerc-network
    restart: unless-stopped
    stop_grace_period: 30s
    healthcheck:
      test: ["CMD", "python", "-c", "import requests; requests.get('http://localhost:8000/health')"]
      interval: 30s
      timeout: 10s
      retries: 3

networks:
  mimerc-network:
    name: mimerc-network

volumes:
  mimerc_postgres_data:
    name: mimerc_postgres_data
EOF

echo "✅ Step 3: Updated docker-compose.yml with correct configuration"

# Step 4: Create test script
cat > test-mimerc.sh << 'EOF'
#!/bin/bash
# Test script for MiMerc agent

echo "🧪 Testing MiMerc Agent..."

# Test 1: Check if agent is running
echo "Test 1: Checking agent health..."
curl -s http://localhost:8002/health || echo "❌ Agent not responding on health endpoint"

# Test 2: Add item to list
echo -e "\nTest 2: Adding items to grocery list..."
curl -X POST http://localhost:8002/chat \
  -H "Content-Type: application/json" \
  -d '{
    "message": "Add milk, eggs, and bread to my grocery list",
    "thread_id": "test-family-list"
  }' | python -m json.tool

# Test 3: View list
echo -e "\nTest 3: Viewing grocery list..."
curl -X POST http://localhost:8002/chat \
  -H "Content-Type: application/json" \
  -d '{
    "message": "What is on my grocery list?",
    "thread_id": "test-family-list"
  }' | python -m json.tool

# Test 4: Check database tables
echo -e "\nTest 4: Checking database tables..."
docker exec mimerc-postgres psql -U mimerc -d mimerc_db -c "\dt" 2>/dev/null | grep checkpoint

echo -e "\n✅ Tests complete!"
EOF
chmod +x test-mimerc.sh

echo "✅ Step 4: Created test script"

echo ""
echo "🚀 FIX INSTRUCTIONS:"
echo "==================="
echo ""
echo "1. CRITICAL: Edit .env and add your OpenAI API key:"
echo "   nano .env"
echo "   Replace: sk-YOUR_ACTUAL_OPENAI_API_KEY_HERE"
echo "   With: Your actual OpenAI API key"
echo ""
echo "2. Clean restart with new schema:"
echo "   docker-compose down -v"
echo "   docker-compose up --build"
echo ""
echo "3. After containers start, run tests:"
echo "   ./test-mimerc.sh"
echo ""
echo "📝 Files created:"
echo "  - init-tables.sql (correct PostgresSaver schema)"
echo "  - .env (template - ADD YOUR KEY!)"
echo "  - docker-compose.yml (updated configuration)"
echo "  - test-mimerc.sh (test script)"
