#!/bin/bash

# Test Script for Commercial Parity Implementation
# Tests intent classification and routing locally

set -e

echo "🧪 Testing Commercial Parity Implementation"
echo "=========================================="
echo ""

# Test 1: Casual Chat Intent
echo "Test 1: Casual Chat Intent Classification"
echo "------------------------------------------"
python3 << 'EOF'
import sys
sys.path.insert(0, './agent')

from main import classify_intent

test_queries = [
    "hello",
    "how are you?",
    "what's up?",
    "good morning",
]

print("Testing casual chat queries:")
for query in test_queries:
    result = classify_intent(query)
    status = "✅" if result.intent == "CASUAL_CHAT" else "❌"
    print(f"{status} '{query}' → {result.intent} (confidence: {result.confidence:.2f})")
EOF

echo ""

# Test 2: Complex Task Intent
echo "Test 2: Complex Task Intent Classification"
echo "------------------------------------------"
python3 << 'EOF'
import sys
sys.path.insert(0, './agent')

from main import classify_intent

test_queries = [
    "analyze this dataset and create visualizations",
    "build a web scraper for this site",
    "help me debug this code",
    "create a REST API for user management",
]

print("Testing complex task queries:")
for query in test_queries:
    result = classify_intent(query)
    status = "✅" if result.intent == "COMPLEX_TASK" else "❌"
    print(f"{status} '{query}' → {result.intent} (confidence: {result.confidence:.2f})")
EOF

echo ""

# Test 3: Knowledge Query Intent
echo "Test 3: Knowledge Query Intent Classification"
echo "---------------------------------------------"
python3 << 'EOF'
import sys
sys.path.insert(0, './agent')

from main import classify_intent

test_queries = [
    "what did we discuss yesterday?",
    "remind me about our last conversation",
    "what was that project we talked about?",
    "tell me about my preferences",
]

print("Testing knowledge query queries:")
for query in test_queries:
    result = classify_intent(query)
    status = "✅" if result.intent == "KNOWLEDGE_QUERY" else "❌"
    print(f"{status} '{query}' → {result.intent} (confidence: {result.confidence:.2f})")
EOF

echo ""
echo "=========================================="
echo "✅ Intent classification tests complete!"
echo ""
