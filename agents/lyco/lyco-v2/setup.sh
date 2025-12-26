#!/bin/bash

# Lyco 2.0 Setup Script
# This script sets up the Lyco 2.0 environment

set -e

echo "🚀 Setting up Lyco 2.0..."

# Check for Python 3.11+
if ! python3 --version | grep -E "3\.(11|12)" > /dev/null; then
    echo "❌ Python 3.11+ is required"
    exit 1
fi

# Check if .env exists
if [ ! -f .env ]; then
    echo "📝 Creating .env file from template..."
    cp .env.example .env
    echo "⚠️  Please edit .env with your API keys and configuration"
    echo "   Required: SUPABASE_URL, SUPABASE_ANON_KEY, ANTHROPIC_API_KEY"
    exit 1
fi

# Create virtual environment
echo "🐍 Creating Python virtual environment..."
python3 -m venv venv

# Activate virtual environment
source venv/bin/activate

# Install dependencies
echo "📦 Installing Python dependencies..."
pip install --upgrade pip
pip install -r requirements.txt

# Make CLI executable
chmod +x cli.py
chmod +x server.py
chmod +x processor.py

echo "✅ Setup complete!"
echo ""
echo "📋 Next steps:"
echo "1. Configure your .env file with API keys"
echo "2. Run the SQL schema in Supabase dashboard"
echo "3. Test with: ./venv/bin/python cli.py test"
echo "4. Start server: ./venv/bin/python server.py"
echo "5. Or use Docker: docker-compose up"
