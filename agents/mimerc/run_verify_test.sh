#!/bin/bash
# Run verification test for MiMerc state persistence fix

echo "================================"
echo "MiMerc State Persistence Test"
echo "================================"
echo ""

# Check if python3 is available
if ! command -v python3 &> /dev/null; then
    echo "❌ ERROR: python3 is not installed"
    echo "Please install Python 3"
    exit 1
fi

echo "✓ Python3 found: $(which python3)"
echo ""

# Check if Docker is running
if docker info &> /dev/null; then
    echo "✓ Docker is running"
    
    # Check if PostgreSQL container is running
    if docker ps | grep -q mimerc-postgres; then
        echo "✓ PostgreSQL container is running"
        echo ""
        
        # For local testing, we need to use localhost:5433 (mapped port)
        echo "📝 Setting up local environment variables..."
        export OPENAI_API_KEY=$(grep OPENAI_API_KEY .env | cut -d '=' -f2)
        export PG_CONNINFO="postgresql://mimerc:mimerc_secure_password@localhost:5433/mimerc_db"
        
        echo "🧪 Running verification test..."
        echo ""
        python3 verify_fix.py
    else
        echo "⚠️  PostgreSQL container is not running"
        echo ""
        echo "Starting Docker containers..."
        docker-compose up -d mimerc-postgres
        
        echo "⏳ Waiting for PostgreSQL to be ready..."
        sleep 5
        
        # Retry with updated connection
        export OPENAI_API_KEY=$(grep OPENAI_API_KEY .env | cut -d '=' -f2)
        export PG_CONNINFO="postgresql://mimerc:mimerc_secure_password@localhost:5433/mimerc_db"
        
        echo "🧪 Running verification test..."
        echo ""
        python3 verify_fix.py
    fi
else
    echo "❌ Docker is not running"
    echo ""
    echo "Please start Docker Desktop or run:"
    echo "  docker-compose up -d mimerc-postgres"
    echo ""
    echo "Then run this script again."
    exit 1
fi
