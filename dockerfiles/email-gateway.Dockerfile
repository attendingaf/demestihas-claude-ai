FROM python:3.9-slim

# Install system dependencies
RUN apt-get update && apt-get install -y \
    build-essential \
    curl \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Install Python dependencies
RUN pip install --no-cache-dir \
    aiohttp>=3.8.0 \
    google-auth>=2.0.0 \
    google-auth-oauthlib>=1.0.0 \
    google-auth-httplib2>=0.2.0 \
    google-api-python-client>=2.0.0 \
    python-dotenv>=1.0.0 \
    aiosmtplib>=2.0.0

# Copy application files
COPY email-gateway.py ./

# Create necessary directories
RUN mkdir -p /app/logs /app/credentials

# Set environment
ENV PYTHONUNBUFFERED=1

# Expose port (if needed for health checks)
EXPOSE 8082

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=15s --retries=3 \
    CMD python -c "import sys; sys.exit(0)" || exit 1

# Start the email gateway
CMD ["python", "email-gateway.py"]
