FROM python:3.11-slim

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    gcc \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements first for better caching
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY . .

# Make claude_interface.py executable
RUN chmod +x claude_interface.py

# Add alias for easy access
RUN echo 'alias huata="python /app/claude_interface.py"' >> /etc/bash.bashrc

# Create non-root user for security
RUN useradd -m -u 1000 huata && chown -R huata:huata /app
USER huata

# Expose port
EXPOSE 8003

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD python -c "import requests; r = requests.get('http://localhost:8003/health/simple'); exit(0 if r.status_code == 200 else 1)"

# Run the application with health endpoint fix
CMD ["python", "app_health_fix.py"]
