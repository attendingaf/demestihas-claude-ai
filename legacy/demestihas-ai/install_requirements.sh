#!/bin/bash
echo "Installing required packages for Intelligent Lyco Bot..."

# Core packages
pip3 install --no-cache-dir \
    python-telegram-bot==20.7 \
    python-dotenv==1.0.0 \
    redis==5.0.1 \
    notion-client==2.2.1 \
    anthropic==0.39.0

# LangChain packages
pip3 install --no-cache-dir \
    langchain==0.3.0 \
    langchain-anthropic==0.3.0 \
    langchain-community==0.3.0 \
    langchain-core==0.3.0

# Additional dependencies
pip3 install --no-cache-dir \
    pydantic==2.5.0 \
    aiohttp==3.9.1

echo "Installation complete!"
