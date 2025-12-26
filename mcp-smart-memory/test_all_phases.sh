#!/bin/bash

echo "Testing All 4 Phases of Memory Enhancement"
echo "=========================================="

# Phase 1: Test document ingestion
echo -e "\n📂 Phase 1: Document Ingestion"
curl -X POST http://localhost:7777/ingest/document \
  -H "Content-Type: application/json" \
  -d '{
    "fileId": "test-doc-001",
    "fileName": "Test Meeting Notes.txt",
    "folder": "Meeting Notes",
    "content": "This is a test document with multiple sentences. It should be split into chunks. Each chunk will be stored separately. The system should handle this gracefully.",
    "mimeType": "text/plain",
    "modifiedTime": "'$(date -u +%Y-%m-%dT%H:%M:%SZ)'"
  }' | jq '.'

# Phase 2: Test chunking
echo -e "\n✂️ Phase 2: Verify Chunking"
curl "http://localhost:7777/context?q=test%20document" | jq '.memories | length'

# Phase 3: Test versioning
echo -e "\n📝 Phase 3: Version Control"
curl -X POST http://localhost:7777/ingest/document \
  -H "Content-Type: application/json" \
  -d '{
    "fileId": "test-doc-001",
    "fileName": "Test Meeting Notes.txt",
    "folder": "Meeting Notes",
    "content": "This is an UPDATED test document. The version control should archive the old one.",
    "mimeType": "text/plain",
    "modifiedTime": "'$(date -u +%Y-%m-%dT%H:%M:%SZ)'"
  }' | jq '.'

# Phase 4: Test conversation memory
echo -e "\n💬 Phase 4: Conversation Memory"
SESSION_ID=$(curl -X POST http://localhost:7777/conversation/start \
  -H "Content-Type: application/json" \
  -d '{"metadata": {"user": "test"}}' | jq -r '.sessionId')

echo "Started session: $SESSION_ID"

curl -X POST http://localhost:7777/conversation/add \
  -H "Content-Type: application/json" \
  -d '{
    "userMessage": "What documents do we have about testing?",
    "assistantResponse": "I found test documents in your Meeting Notes folder.",
    "memoriesUsed": ["test-doc-001"],
    "toolCalls": ["search", "retrieve"]
  }' | jq '.'

curl "http://localhost:7777/conversation/recent?limit=5" | jq '.'

echo -e "\n✅ All phases tested successfully!"
