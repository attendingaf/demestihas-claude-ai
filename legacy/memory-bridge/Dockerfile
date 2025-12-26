FROM python:3.12-slim

WORKDIR /app

# Install dependencies
RUN pip install --no-cache-dir anthropic qdrant-client pyyaml requests

# Copy application files
COPY extract_facts.py /app/
COPY config.yaml /app/
COPY mene-jwt-token.json /app/

# Set environment variables
ENV LOG_DIR=/app
ENV PYTHONUNBUFFERED=1

# Default command (can be overridden)
CMD ["python3", "extract_facts.py", "--hours", "24"]
