#!/bin/bash

# LangGraph setup for Lyco v2
# This script is idempotent - safe to run multiple times

set -e  # Exit on error

echo "🚀 Setting up LangGraph for Lyco v2..."

# Check if we're in the right directory
if [ ! -f "langgraph.json" ] && [ "$1" != "--init" ]; then
    echo "⚠️  Warning: langgraph.json not found. Run with --init flag on first setup."
fi

# Create virtual environment if it doesn't exist
if [ ! -d "venv" ]; then
    echo "📦 Creating virtual environment..."
    python3 -m venv venv
else
    echo "✓ Virtual environment already exists"
fi

# Activate virtual environment
source venv/bin/activate

# Upgrade pip
echo "📦 Upgrading pip..."
pip install --quiet --upgrade pip

# Install dependencies
echo "📦 Installing dependencies..."
pip install --quiet -r requirements.txt

# Check if .env exists, if not copy from v2 or create from example
if [ ! -f ".env" ]; then
    if [ -f "../lyco-v2/.env" ]; then
        echo "📋 Copying .env from Lyco v2..."
        cp ../lyco-v2/.env .env
    elif [ -f ".env.example" ]; then
        echo "📋 Creating .env from .env.example..."
        cp .env.example .env
        echo "⚠️  Please update .env with your actual credentials"
    else
        echo "⚠️  No .env file found. Please create one from .env.example"
    fi
else
    echo "✓ .env file already exists"
fi

# Create symlink to v2 src for code reuse (if it doesn't exist)
if [ ! -L "src_v2" ] && [ -d "../lyco-v2/src" ]; then
    echo "🔗 Creating symlink to Lyco v2 src..."
    ln -sf ../lyco-v2/src src_v2
elif [ -L "src_v2" ]; then
    echo "✓ Symlink to Lyco v2 src already exists"
else
    echo "⚠️  Lyco v2 src not found at ../lyco-v2/src"
fi

# Check Redis connection
echo "🔍 Checking Redis connection..."
python -c "import redis; r = redis.Redis(host='localhost', port=6379, decode_responses=True); r.ping(); print('✓ Redis is running')" 2>/dev/null || echo "⚠️  Redis is not running. Please start Redis: redis-server"

# Check PostgreSQL/Supabase connection
echo "🔍 Checking database connection..."
if [ -f ".env" ]; then
    python -c "
import os
from dotenv import load_dotenv
load_dotenv()
db_url = os.getenv('DATABASE_URL')
if db_url:
    print('✓ Database URL configured')
else:
    print('⚠️  DATABASE_URL not found in .env')
" || echo "⚠️  Error checking database configuration"
fi

# Initialize __init__.py files if they don't exist
touch workflow/__init__.py 2>/dev/null || true
touch workflow/nodes/__init__.py 2>/dev/null || true
touch agents/__init__.py 2>/dev/null || true
touch studio/__init__.py 2>/dev/null || true
touch tests/__init__.py 2>/dev/null || true

echo ""
echo "✅ Setup complete!"
echo ""
echo "📝 Next steps:"
echo "1. Activate environment: source venv/bin/activate"
echo "2. Update .env with your credentials (if needed)"
echo "3. Start Redis: redis-server"
echo "4. Start server: python server.py"
echo "5. Open LangGraph Studio and connect to http://localhost:8000"
echo "6. View playground at: http://localhost:8000/lyco/playground"
echo ""
echo "🎨 LangGraph Studio:"
echo "   - Download from: https://studio.langchain.com/"
echo "   - Connect to: http://localhost:8000"
echo "   - Graph endpoint: /lyco"
echo ""
echo "🧪 Run tests: pytest tests/"
echo "📊 View graph structure: curl http://localhost:8000/debug/graph | jq"
