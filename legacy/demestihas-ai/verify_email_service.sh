#!/bin/bash
echo "🔍 Checking email service files..."
ls -la email_webhook.py email_parser.py Dockerfile.email 2>/dev/null
if [ $? -eq 0 ]; then
    echo "✅ All files present"
else
    echo "❌ Some files missing - need to upload implementation"
fi
