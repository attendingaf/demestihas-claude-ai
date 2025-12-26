#!/bin/bash

echo "🔍 Email Service Deployment Verification Script"
echo "============================================="
echo ""

# Check if required files exist
echo "📁 Checking required files..."
echo ""

FILES=(
    "email_webhook.py"
    "email_parser.py"
    "Dockerfile.email"
)

MISSING_FILES=0

for file in "${FILES[@]}"; do
    if [ -f "$file" ]; then
        echo "✅ $file exists ($(ls -lh $file | awk '{print $5}'))"
    else
        echo "❌ $file is MISSING!"
        MISSING_FILES=$((MISSING_FILES + 1))
    fi
done

echo ""

# Check environment variables
echo "🔧 Checking environment variables..."
echo ""

if [ -f .env ]; then
    echo "✅ .env file exists"
    
    # Check for required variables
    if grep -q "ANTHROPIC_API_KEY" .env; then
        echo "✅ ANTHROPIC_API_KEY configured"
    else
        echo "⚠️  ANTHROPIC_API_KEY not found in .env"
    fi
    
    if grep -q "NOTION_TOKEN" .env; then
        echo "✅ NOTION_TOKEN configured"
    else
        echo "⚠️  NOTION_TOKEN not found in .env"
    fi
    
    if grep -q "SENDGRID" .env; then
        echo "✅ SENDGRID key configured"
    else
        echo "⚠️  SENDGRID_WEBHOOK_KEY not configured (optional for now)"
    fi
else
    echo "❌ .env file not found!"
fi

echo ""

# Check Docker status
echo "🐳 Checking Docker status..."
echo ""

if docker ps > /dev/null 2>&1; then
    echo "✅ Docker is running"
    
    # Check for Redis
    if docker ps | grep -q "lyco-redis"; then
        echo "✅ Redis container is running"
    else
        echo "❌ Redis container not running (required for email queue)"
    fi
    
    # Check if email container exists (might be stopped)
    if docker ps -a | grep -q "demestihas-email"; then
        echo "⚠️  Email container exists but may need restart"
        docker ps -a | grep "demestihas-email"
    else
        echo "ℹ️  Email container not created yet"
    fi
else
    echo "❌ Docker daemon not accessible!"
fi

echo ""

# Check docker-compose.yml
echo "📋 Checking docker-compose.yml..."
if [ -f docker-compose.yml ]; then
    if grep -q "email-webhook:" docker-compose.yml; then
        echo "⚠️  email-webhook service exists in docker-compose.yml (may need fixing)"
    else
        echo "ℹ️  email-webhook service not in docker-compose.yml yet"
    fi
else
    echo "❌ docker-compose.yml not found!"
fi

echo ""

# Summary
echo "📊 Summary:"
echo "==========="

if [ $MISSING_FILES -eq 0 ]; then
    echo "✅ All required files present"
    echo ""
    echo "Ready to run: ./fix_email_service_compose.sh"
else
    echo "❌ Missing $MISSING_FILES required files"
    echo ""
    echo "The email service files may not have been uploaded to the VPS."
    echo "Need to upload the implementation files first."
fi

echo ""
echo "🔧 Quick Fix Commands:"
echo "----------------------"
echo "1. To fix docker-compose: ./fix_email_service_compose.sh"
echo "2. To check logs: docker logs demestihas-email"
echo "3. To restart service: docker-compose restart email-webhook"
echo "4. To rebuild: docker-compose build email-webhook && docker-compose up -d email-webhook"
