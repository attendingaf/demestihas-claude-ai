FROM python:3.11-slim

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    gcc \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements first for better caching
COPY agents/lyco/lyco-v2/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY agents/lyco/lyco-v2/ .

# Create credentials directory
RUN mkdir -p credentials

# Make scripts executable
RUN chmod +x cli.py server.py

# Health check
HEALTHCHECK --interval=30s --timeout=3s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:8000/api/health || exit 1

# Expose port
EXPOSE 8000

# Default command runs the server
CMD ["python", "server.py"]
