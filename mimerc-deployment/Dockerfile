FROM python:3.11-alpine

# Install system dependencies for PostgreSQL and Rust (for tiktoken)
RUN apk add --no-cache \
    gcc \
    musl-dev \
    postgresql-dev \
    python3-dev \
    libffi-dev \
    cargo \
    rust

# Set working directory
WORKDIR /app

# Copy requirements file
COPY requirements.txt .

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY agent.py .
COPY telegram_bot.py .

# Create non-root user with UID 1000
RUN adduser -D -u 1000 mimerc && \
    chown -R mimerc:mimerc /app

# Switch to non-root user
USER mimerc

# Health check to ensure database connectivity
HEALTHCHECK --interval=30s --timeout=3s --start-period=5s --retries=3 \
    CMD python -c "import psycopg; print('healthy')" || exit 1

# Set environment variable for real-time logs
ENV PYTHONUNBUFFERED=1

# Default to running agent, but can be overridden
CMD ["python", "agent.py"]
