FROM python:3.9-slim

# Install system dependencies
RUN apt-get update && apt-get install -y \
    build-essential \
    sqlite3 \
    curl \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Install Python dependencies
RUN pip install --no-cache-dir \
    aiohttp>=3.8.0 \
    python-dotenv>=1.0.0

# Copy application files
COPY notion-lyco-sync.py ./
COPY field-mappings.json ./

# Create necessary directories
RUN mkdir -p /app/logs/sync-audit /app/data

# Set environment
ENV PYTHONUNBUFFERED=1

# Expose port (if needed for health checks)
EXPOSE 8083

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=15s --retries=3 \
    CMD python -c "import sys; sys.exit(0)" || exit 1

# Start the sync bridge
CMD ["python", "notion-lyco-sync.py"]
