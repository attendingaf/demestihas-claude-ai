FROM python:3.9-slim

# Install system dependencies
RUN apt-get update && apt-get install -y \
    build-essential \
    curl \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Install Python dependencies
RUN pip install --no-cache-dir \
    prompt_toolkit>=3.0.0 \
    websockets>=11.0 \
    aiohttp>=3.8.0 \
    python-dotenv>=1.0.0 \
    colorama \
    rich

# Copy application files
COPY terminal-capture.py ./

# Create necessary directories
RUN mkdir -p /app/logs/brain-dumps

# Set environment
ENV PYTHONUNBUFFERED=1

# Health check (not applicable for interactive terminal)
# This is an interactive service, no healthcheck needed

# Start the terminal capture
CMD ["python", "terminal-capture.py"]
