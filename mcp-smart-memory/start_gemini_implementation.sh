#!/bin/bash

# Quick Start Script for Gemini CLI Implementation
# Run this to set up the Google Drive Integration project

echo "🚀 Setting up Google Drive Integration with Memory System"
echo "========================================================="

# Navigate to project
cd ~/Projects/demestihas-ai/mcp-smart-memory

# Create backup
echo "📦 Creating backup..."
cp -r . ../mcp-smart-memory-backup-$(date +%Y%m%d-%H%M%S)

# Install dependencies
echo "📚 Installing dependencies..."
npm install googleapis natural

# Create test script
cat > test_gemini_implementation.sh << 'EOF'
#!/bin/bash

echo "Testing Gemini CLI Implementation"
echo "================================="

# Check if API is running
if curl -s http://localhost:7777/health > /dev/null; then
    echo "✅ Memory API is running"
else
    echo "❌ Memory API not running. Start with: npm start"
    exit 1
fi

# Test document ingestion
echo -e "\nTesting document ingestion..."
RESPONSE=$(curl -s -X POST http://localhost:7777/ingest/document \
  -H "Content-Type: application/json" \
  -d '{
    "fileId": "gemini-test-001",
    "fileName": "Gemini Test Document.txt",
    "folder": "Testing",
    "content": "This document was ingested by Gemini CLI implementation. It tests the new chunking system. Each sentence should become part of a chunk. The versioning system will prevent duplicates.",
    "mimeType": "text/plain",
    "modifiedTime": "'$(date -u +%Y-%m-%dT%H:%M:%SZ)'"
  }')

if echo "$RESPONSE" | grep -q "success"; then
    echo "✅ Document ingestion working"
    echo "$RESPONSE" | jq '.'
else
    echo "❌ Document ingestion failed"
    echo "$RESPONSE"
fi

# Test retrieval of chunks
echo -e "\nTesting chunk retrieval..."
CHUNKS=$(curl -s "http://localhost:7777/context?q=Gemini%20CLI")
if echo "$CHUNKS" | grep -q "Gemini"; then
    echo "✅ Chunk retrieval working"
    echo "Found $(echo "$CHUNKS" | jq '.total_memories') chunks"
else
    echo "❌ Chunk retrieval failed"
fi

# Test conversation memory
echo -e "\nTesting conversation memory..."
SESSION=$(curl -s -X POST http://localhost:7777/conversation/start \
  -H "Content-Type: application/json" \
  -d '{"metadata": {"tool": "gemini_cli"}}')

if echo "$SESSION" | grep -q "sessionId"; then
    echo "✅ Conversation memory working"
    SESSION_ID=$(echo "$SESSION" | jq -r '.sessionId')
    echo "Session ID: $SESSION_ID"
else
    echo "❌ Conversation memory failed"
fi

echo -e "\n✅ Gemini implementation test complete!"
EOF

chmod +x test_gemini_implementation.sh

echo ""
echo "📝 Instructions for Gemini CLI with Zed:"
echo "----------------------------------------"
echo "1. Open project in Zed:"
echo "   zed ~/Projects/demestihas-ai/mcp-smart-memory"
echo ""
echo "2. Open the handoff document:"
echo "   View GEMINI_HANDOFF_GDRIVE_INTEGRATION.md"
echo ""
echo "3. Use Gemini to implement each phase:"
echo "   - Select Phase 1 code in the handoff"
echo "   - Run: gemini 'Create gdrive-monitor.js with this code'"
echo "   - Select Phase 2 code"  
echo "   - Run: gemini 'Add these endpoints to memory-api.js'"
echo "   - Continue for each phase..."
echo ""
echo "4. Test implementation:"
echo "   ./test_gemini_implementation.sh"
echo ""
echo "5. Start the services:"
echo "   npm start                    # Terminal 1"
echo "   node gdrive-monitor.js       # Terminal 2"
echo ""
echo "Ready to implement with Gemini CLI! 🎉"
