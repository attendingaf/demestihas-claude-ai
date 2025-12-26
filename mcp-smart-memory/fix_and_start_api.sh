#!/bin/bash

echo "Fixing MCP Memory System Issues"
echo "================================"

# 1. Kill existing process on port 7777
echo "Step 1: Clearing port 7777..."
PID=$(lsof -t -i:7777)
if [ ! -z "$PID" ]; then
    kill -9 $PID
    echo "  ✓ Killed process $PID"
else
    echo "  ✓ Port already clear"
fi

# 2. Navigate to project
cd ~/Projects/demestihas-ai/mcp-smart-memory

# 3. Check/install dependencies
echo -e "\nStep 2: Checking dependencies..."
if [ ! -d "node_modules" ]; then
    echo "  Installing dependencies..."
    npm install
else
    echo "  ✓ Dependencies installed"
fi

# 4. Check for RAG system
echo -e "\nStep 3: Checking RAG system..."
if [ -d "../claude-desktop-rag" ]; then
    echo "  ✓ RAG system found"
    
    # Install RAG dependencies if needed
    if [ ! -d "../claude-desktop-rag/node_modules" ]; then
        echo "  Installing RAG dependencies..."
        cd ../claude-desktop-rag
        npm install
        cd ../mcp-smart-memory
    fi
else
    echo "  ⚠ RAG system not found - will use mock implementation"
fi

# 5. Create initialization patch
echo -e "\nStep 4: Creating initialization patch..."
cat > memory-api-patch.js << 'EOF'
// Patch for contextRetriever initialization issue
const fs = require('fs');
const path = require('path');

const apiFile = path.join(__dirname, 'memory-api.js');
let content = fs.readFileSync(apiFile, 'utf8');

// Fix the initialization issue
if (content.includes('contextRetriever.initialize')) {
    content = content.replace(
        'await contextRetriever.initialize()',
        'if (contextRetriever.initialize) await contextRetriever.initialize()'
    );
    
    fs.writeFileSync(apiFile, content);
    console.log('  ✓ Patched memory-api.js');
} else {
    console.log('  ✓ No patch needed');
}
EOF

node memory-api-patch.js

# 6. Start the API server
echo -e "\nStep 5: Starting API server..."
npm run api
