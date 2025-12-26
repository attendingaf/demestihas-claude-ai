#!/bin/bash

# Claude Desktop RAG System Setup Script
# Chapter 1: The Memory Palace - Demestihas.ai MAS

set -e

echo "======================================"
echo "Claude Desktop RAG System Setup"
echo "======================================"
echo ""

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Function to print colored output
print_status() {
    echo -e "${GREEN}[✓]${NC} $1"
}

print_error() {
    echo -e "${RED}[✗]${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}[!]${NC} $1"
}

# Check Node.js version
echo "Checking Node.js version..."
NODE_VERSION=$(node -v | cut -d'v' -f2 | cut -d'.' -f1)
if [ "$NODE_VERSION" -lt 18 ]; then
    print_error "Node.js version 18 or higher is required"
    exit 1
fi
print_status "Node.js version is compatible"

# Check if .env exists
echo ""
echo "Checking environment configuration..."
if [ ! -f .env ]; then
    if [ -f .env.template ]; then
        print_warning ".env file not found. Creating from template..."
        cp .env.template .env
        print_status ".env file created from template"
        echo ""
        print_warning "Please edit .env file with your API keys before running the system:"
        echo "  - OPENAI_API_KEY"
        echo "  - SUPABASE_URL"
        echo "  - SUPABASE_ANON_KEY"
        echo ""
    else
        print_error ".env.template not found"
        exit 1
    fi
else
    print_status ".env file exists"
fi

# Install dependencies
echo ""
echo "Installing npm dependencies..."
npm install
print_status "Dependencies installed"

# Create necessary directories
echo ""
echo "Creating required directories..."
mkdir -p data
mkdir -p logs
print_status "Directories created"

# Initialize SQLite database
echo ""
echo "Initializing SQLite database..."
node -e "
import sqliteClient from './src/core/sqlite-client.js';
sqliteClient.initialize().then(() => {
    console.log('SQLite database initialized');
    process.exit(0);
}).catch(err => {
    console.error('Failed to initialize SQLite:', err);
    process.exit(1);
});
" 2>/dev/null || {
    print_warning "Could not auto-initialize SQLite database"
    echo "Database will be initialized on first run"
}

# Check Supabase setup
echo ""
echo "Checking Supabase configuration..."
if grep -q "your_supabase" .env; then
    print_warning "Supabase credentials not configured in .env"
    echo ""
    echo "To complete Supabase setup:"
    echo "1. Create a Supabase project at https://supabase.com"
    echo "2. Run the SQL schema from config/supabase-schema.sql"
    echo "3. Update .env with your Supabase credentials"
    echo ""
else
    print_status "Supabase credentials found in .env"
fi

# Create startup script
echo ""
echo "Creating startup script..."
cat > start.sh << 'EOF'
#!/bin/bash
echo "Starting Claude Desktop RAG System..."
node src/index.js
EOF
chmod +x start.sh
print_status "Startup script created"

# Create index.js if it doesn't exist
if [ ! -f src/index.js ]; then
    echo ""
    echo "Creating main index.js file..."
    cat > src/index.js << 'EOF'
import winston from 'winston';
import extensionHooks from './claude-desktop/extension-hooks.js';
import { config, validateConfig } from '../config/rag-config.js';

const logger = winston.createLogger({
  level: config.logging.level,
  format: winston.format.combine(
    winston.format.timestamp(),
    winston.format.json()
  ),
  transports: [
    new winston.transports.Console({
      format: winston.format.simple()
    }),
    new winston.transports.File({ 
      filename: config.logging.file 
    })
  ]
});

async function main() {
  try {
    // Validate configuration
    validateConfig();
    
    // Initialize extension hooks
    await extensionHooks.initialize();
    
    logger.info('Claude Desktop RAG System started successfully');
    
    // Keep the process running
    process.stdin.resume();
    
    // Handle shutdown gracefully
    process.on('SIGINT', () => {
      logger.info('Shutting down...');
      process.exit(0);
    });
    
  } catch (error) {
    logger.error('Failed to start RAG system:', error);
    process.exit(1);
  }
}

main();
EOF
    print_status "Main index.js file created"
fi

# Run tests
echo ""
echo "Running system tests..."
npm test 2>/dev/null || {
    print_warning "Some tests failed. This may be due to missing API keys."
    echo "Please configure your .env file and run 'npm test' to verify the setup."
}

# Print summary
echo ""
echo "======================================"
echo "Setup Complete!"
echo "======================================"
echo ""
print_status "Claude Desktop RAG System is ready"
echo ""
echo "Next steps:"
echo "1. Edit .env file with your API keys"
echo "2. Run the Supabase schema (config/supabase-schema.sql)"
echo "3. Start the system with: ./start.sh"
echo "4. Run tests with: npm test"
echo ""
echo "For Claude Desktop integration:"
echo "- Import the extension hooks in your Claude Desktop config"
echo "- Use the context injector for prompt augmentation"
echo "- Enable response handling for pattern detection"
echo ""
echo "Documentation:"
echo "- README.md for detailed instructions"
echo "- config/rag-config.js for configuration options"
echo "- scripts/test-pipeline.js for testing examples"
echo ""