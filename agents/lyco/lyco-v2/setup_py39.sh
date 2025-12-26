#!/bin/bash

# Lyco 2.0 Setup Script - Python 3.9 Compatible Version
# This script sets up the Lyco 2.0 environment for Python 3.9+

set -e

echo "🚀 Setting up Lyco 2.0 (Python 3.9 compatible)..."

# Check for Python 3.9+
if ! python3 --version | grep -E "3\.(9|10|11|12)" > /dev/null; then
    echo "❌ Python 3.9+ is required"
    exit 1
fi

echo "✅ Found Python: $(python3 --version)"

# Check if .env exists
if [ ! -f .env ]; then
    echo "📝 Creating .env file from template..."
    cp .env.example .env
    echo ""
    echo "⚠️  IMPORTANT: Edit .env with your API keys before continuing"
    echo "   Required values:"
    echo "   - SUPABASE_URL=your_supabase_url"
    echo "   - SUPABASE_ANON_KEY=your_supabase_anon_key"
    echo "   - ANTHROPIC_API_KEY=your_anthropic_api_key"
    echo ""
    echo "After editing .env, run this script again."
    exit 1
fi

# Create virtual environment
echo "🐍 Creating Python virtual environment..."
python3 -m venv venv

# Activate virtual environment
source venv/bin/activate

# Upgrade pip first
echo "📦 Upgrading pip..."
pip install --upgrade pip

# Install dependencies with compatibility fixes
echo "📦 Installing Python dependencies..."
# Install typing_extensions for better compatibility
pip install typing_extensions

# Install main requirements
pip install -r requirements.txt || {
    echo "⚠️  Some packages may have issues with Python 3.9"
    echo "Attempting individual installation..."
    
    # Install packages one by one for better error handling
    pip install supabase==2.5.1
    pip install anthropic==0.31.2
    pip install openai==1.37.0
    pip install redis==5.0.7
    pip install click==8.1.7
    pip install python-dotenv==1.0.1
    pip install aiohttp==3.9.5
    pip install pydantic==2.8.2
    pip install uvicorn==0.30.3
    pip install fastapi==0.111.1
}

# Make CLI executable
chmod +x cli.py
chmod +x server.py
chmod +x processor.py

echo ""
echo "✅ Setup complete with Python 3.9!"
echo ""
echo "📋 Next steps:"
echo "1. Verify your .env file has API keys configured"
echo "2. Run the SQL schema in Supabase dashboard (copy from schema.sql)"
echo "3. Test with: source venv/bin/activate && python cli.py test"
echo "4. Start server: source venv/bin/activate && python server.py"
echo ""
echo "Note: Some async features may work differently in Python 3.9 vs 3.11"
echo "If you encounter issues, consider installing Python 3.11+ or using Docker"
