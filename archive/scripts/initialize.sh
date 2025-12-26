#!/bin/bash

# Demestihas AI Suite - Project Initialization Script
# This script sets up the complete project structure and initial configuration

set -e  # Exit on error

echo "🚀 Initializing Demestihas AI Suite..."

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Project root
PROJECT_ROOT="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"

# Function to create directory structure
create_directories() {
    echo -e "${YELLOW}📁 Creating directory structure...${NC}"
    
    # Claude Desktop directories
    mkdir -p "$PROJECT_ROOT/claude-desktop"/{docs,src,patterns,config,lib,tests}
    mkdir -p "$PROJECT_ROOT/claude-desktop/src"/{rag,patterns,automation,context}
    
    # Notion Automation directories
    mkdir -p "$PROJECT_ROOT/notion-automation"/{workflows,templates,integrations,config}
    
    # Hermes Audio directories (if not exists)
    mkdir -p "$PROJECT_ROOT/hermes_audio"/{transcription,meeting-notes,action-items,integrations}
    
    # Shared Intelligence directories
    mkdir -p "$PROJECT_ROOT/shared-intelligence"/{knowledge-base,patterns,embeddings,team-learning}
    
    # Deployment directories
    mkdir -p "$PROJECT_ROOT/deployment"/{docker,nginx,monitoring,backup}
    
    # Core Infrastructure directories
    mkdir -p "$PROJECT_ROOT/core-infrastructure"/{supabase,redis,message-queue,api-gateway}
    
    # Documentation directories
    mkdir -p "$PROJECT_ROOT/docs"/{api,guides,architecture}
    
    echo -e "${GREEN}✅ Directory structure created${NC}"
}

# Function to initialize git repository
init_git() {
    echo -e "${YELLOW}🔧 Initializing Git repository...${NC}"
    
    if [ ! -d "$PROJECT_ROOT/.git" ]; then
        git init
        
        # Create .gitignore
        cat > "$PROJECT_ROOT/.gitignore" << EOF
# Node
node_modules/
*.log
npm-debug.log*
yarn-debug.log*
yarn-error.log*

# Environment
.env
.env.local
.env.*.local

# IDE
.vscode/
.idea/
*.swp
*.swo
.DS_Store

# Build
dist/
build/
*.pyc
__pycache__/

# Data
*.db
*.sqlite
data/
cache/

# Secrets
*.key
*.pem
secrets/
credentials/

# Temporary
tmp/
temp/
*.tmp

# Logs
logs/
*.log

# Coverage
coverage/
.nyc_output/
EOF
        
        echo -e "${GREEN}✅ Git repository initialized${NC}"
    else
        echo -e "${YELLOW}ℹ️  Git repository already exists${NC}"
    fi
}

# Function to create package.json for Node.js components
create_package_json() {
    echo -e "${YELLOW}📦 Creating package.json...${NC}"
    
    cat > "$PROJECT_ROOT/package.json" << EOF
{
  "name": "demestihas-ai-suite",
  "version": "1.0.0",
  "description": "Multi-Agent Custom AI Ecosystem",
  "main": "index.js",
  "scripts": {
    "setup": "node scripts/setup.js",
    "configure-profile": "node scripts/configure-profile.js",
    "test-rag": "node scripts/test-rag.js",
    "start-enhanced": "node claude-desktop/src/index.js",
    "enable-rag": "node scripts/enable-feature.js rag",
    "enable-patterns": "node scripts/enable-feature.js patterns",
    "enable-automation": "node scripts/enable-feature.js automation",
    "diagnose": "node scripts/diagnose.js",
    "health-check": "node scripts/health-check.js",
    "reset-cache": "node scripts/reset-cache.js",
    "dev": "nodemon claude-desktop/src/index.js",
    "test": "jest"
  },
  "keywords": ["ai", "automation", "rag", "claude", "notion", "productivity"],
  "author": "Mene Demestihas",
  "license": "Proprietary",
  "dependencies": {
    "@supabase/supabase-js": "^2.39.0",
    "openai": "^4.24.0",
    "dotenv": "^16.3.1",
    "express": "^4.18.2",
    "redis": "^4.6.11",
    "js-yaml": "^4.1.0",
    "axios": "^1.6.2",
    "winston": "^3.11.0",
    "node-cron": "^3.0.3",
    "uuid": "^9.0.1"
  },
  "devDependencies": {
    "nodemon": "^3.0.2",
    "jest": "^29.7.0",
    "@types/node": "^20.10.5",
    "eslint": "^8.56.0"
  }
}
EOF
    
    echo -e "${GREEN}✅ package.json created${NC}"
}

# Function to create environment template
create_env_template() {
    echo -e "${YELLOW}🔐 Creating environment template...${NC}"
    
    cat > "$PROJECT_ROOT/.env.template" << EOF
# Demestihas AI Suite Configuration

# Supabase
SUPABASE_URL=your_supabase_project_url
SUPABASE_ANON_KEY=your_supabase_anon_key
SUPABASE_SERVICE_KEY=your_supabase_service_key

# OpenAI
OPENAI_API_KEY=your_openai_api_key
OPENAI_ORG_ID=your_openai_org_id

# Redis (optional for caching)
REDIS_URL=redis://localhost:6379
REDIS_PASSWORD=

# Claude Desktop
CLAUDE_DESKTOP_HOME=~/claude-desktop
ENABLE_PROACTIVE_SUGGESTIONS=true
ENABLE_AUTO_DOCUMENTATION=true
ENABLE_PATTERN_LEARNING=true
PATTERN_DETECTION_THRESHOLD=3
CONTEXT_WINDOW_SIZE=10000

# Notion
NOTION_API_KEY=your_notion_api_key
NOTION_DATABASE_ID=your_database_id

# System
NODE_ENV=development
LOG_LEVEL=info
PORT=3000

# Features
ENABLE_RAG=true
ENABLE_PATTERNS=true
ENABLE_AUTOMATION=true
ENABLE_TEAM_SHARING=false

# Paths
DATA_DIR=./data
CACHE_DIR=./cache
LOGS_DIR=./logs
EOF
    
    echo -e "${GREEN}✅ Environment template created${NC}"
    echo -e "${YELLOW}ℹ️  Copy .env.template to .env and fill in your values${NC}"
}

# Function to create initial configuration
create_initial_config() {
    echo -e "${YELLOW}⚙️  Creating initial configuration...${NC}"
    
    # Claude Desktop config
    cat > "$PROJECT_ROOT/claude-desktop/config/default.yaml" << EOF
# Claude Desktop Default Configuration

system:
  version: 1.0.0
  mode: enhanced

features:
  rag:
    enabled: true
    embedding_model: text-embedding-3-small
    vector_dimensions: 1536
    similarity_threshold: 0.7
    
  patterns:
    enabled: true
    detection_threshold: 3
    min_confidence: 0.7
    auto_suggest: true
    
  automation:
    enabled: true
    trigger_check_interval: 60000
    max_concurrent_workflows: 5
    
  proactive:
    enabled: true
    suggestion_confidence: 0.8
    morning_routine_time: "09:00"
    eod_summary_time: "17:00"

cache:
  memory:
    enabled: true
    ttl: 3600
    max_size: 100
  redis:
    enabled: false
    ttl: 86400

logging:
  level: info
  file: ./logs/claude-desktop.log
  rotate: daily
  max_files: 7
EOF
    
    echo -e "${GREEN}✅ Initial configuration created${NC}"
}

# Function to create setup scripts
create_setup_scripts() {
    echo -e "${YELLOW}📝 Creating setup scripts...${NC}"
    
    mkdir -p "$PROJECT_ROOT/scripts"
    
    # Main setup script
    cat > "$PROJECT_ROOT/scripts/setup.js" << 'EOF'
#!/usr/bin/env node

const fs = require('fs');
const path = require('path');
const { execSync } = require('child_process');
const readline = require('readline');

const rl = readline.createInterface({
  input: process.stdin,
  output: process.stdout
});

console.log('🚀 Demestihas AI Suite Setup Wizard\n');

async function question(prompt) {
  return new Promise((resolve) => {
    rl.question(prompt, resolve);
  });
}

async function setup() {
  // Check for .env file
  if (!fs.existsSync('.env')) {
    console.log('📝 Creating .env file from template...');
    fs.copyFileSync('.env.template', '.env');
    console.log('✅ .env file created. Please edit it with your API keys.\n');
  }

  // Ask for Supabase setup
  const setupSupabase = await question('Do you want to set up Supabase now? (y/n): ');
  if (setupSupabase.toLowerCase() === 'y') {
    const supabaseUrl = await question('Enter your Supabase URL: ');
    const supabaseKey = await question('Enter your Supabase Anon Key: ');
    
    // Update .env file
    let envContent = fs.readFileSync('.env', 'utf8');
    envContent = envContent.replace('your_supabase_project_url', supabaseUrl);
    envContent = envContent.replace('your_supabase_anon_key', supabaseKey);
    fs.writeFileSync('.env', envContent);
    
    console.log('✅ Supabase configuration saved\n');
  }

  // Ask for OpenAI setup
  const setupOpenAI = await question('Do you want to set up OpenAI now? (y/n): ');
  if (setupOpenAI.toLowerCase() === 'y') {
    const openaiKey = await question('Enter your OpenAI API Key: ');
    
    // Update .env file
    let envContent = fs.readFileSync('.env', 'utf8');
    envContent = envContent.replace('your_openai_api_key', openaiKey);
    fs.writeFileSync('.env', envContent);
    
    console.log('✅ OpenAI configuration saved\n');
  }

  // Install dependencies
  console.log('📦 Installing dependencies...');
  execSync('npm install', { stdio: 'inherit' });
  
  console.log('\n✅ Setup complete!');
  console.log('\nNext steps:');
  console.log('1. Review and update .env file if needed');
  console.log('2. Run "npm run configure-profile" to set up your user profile');
  console.log('3. Run "npm run test-rag" to test RAG connection');
  console.log('4. Run "npm run start-enhanced" to start the enhanced Claude Desktop');
  
  rl.close();
}

setup().catch(console.error);
EOF
    
    chmod +x "$PROJECT_ROOT/scripts/setup.js"
    
    echo -e "${GREEN}✅ Setup scripts created${NC}"
}

# Function to create Docker files
create_docker_files() {
    echo -e "${YELLOW}🐳 Creating Docker configuration...${NC}"
    
    # Main Dockerfile
    cat > "$PROJECT_ROOT/deployment/docker/Dockerfile" << EOF
FROM node:18-alpine

WORKDIR /app

# Copy package files
COPY package*.json ./
RUN npm ci --only=production

# Copy application
COPY . .

# Create necessary directories
RUN mkdir -p /app/data /app/cache /app/logs

# Set environment
ENV NODE_ENV=production

EXPOSE 3000

CMD ["node", "claude-desktop/src/index.js"]
EOF
    
    # Docker Compose file
    cat > "$PROJECT_ROOT/deployment/docker/docker-compose.yml" << EOF
version: '3.8'

services:
  claude-desktop:
    build: 
      context: ../..
      dockerfile: deployment/docker/Dockerfile
    environment:
      - NODE_ENV=production
    env_file:
      - ../../.env
    ports:
      - "3000:3000"
    volumes:
      - data:/app/data
      - logs:/app/logs
    depends_on:
      - redis
    restart: unless-stopped

  redis:
    image: redis:7-alpine
    ports:
      - "6379:6379"
    volumes:
      - redis-data:/data
    restart: unless-stopped

  notion-automation:
    build:
      context: ../..
      dockerfile: deployment/docker/Dockerfile.notion
    env_file:
      - ../../.env
    depends_on:
      - redis
    restart: unless-stopped

  hermes-audio:
    build:
      context: ../..
      dockerfile: deployment/docker/Dockerfile.hermes
    env_file:
      - ../../.env
    depends_on:
      - redis
    restart: unless-stopped

volumes:
  data:
  logs:
  redis-data:
EOF
    
    echo -e "${GREEN}✅ Docker configuration created${NC}"
}

# Main execution
main() {
    echo -e "${GREEN}"
    echo "╔══════════════════════════════════════╗"
    echo "║   DEMESTIHAS AI SUITE INITIALIZER    ║"
    echo "╚══════════════════════════════════════╝"
    echo -e "${NC}"
    
    create_directories
    init_git
    create_package_json
    create_env_template
    create_initial_config
    create_setup_scripts
    create_docker_files
    
    echo -e "\n${GREEN}✨ Initialization complete!${NC}"
    echo -e "\n${YELLOW}Next steps:${NC}"
    echo "1. Copy .env.template to .env and add your API keys"
    echo "2. Run 'npm install' to install dependencies"
    echo "3. Run 'npm run setup' for interactive setup"
    echo "4. Check README.md for detailed documentation"
    
    echo -e "\n${GREEN}Happy building! 🚀${NC}"
}

# Run main function
main
