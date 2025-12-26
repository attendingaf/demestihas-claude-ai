FROM python:3.10-slim

WORKDIR /app

# Install curl for health checks
RUN apt-get update && \
    apt-get install -y curl && \
    apt-get clean && \
    rm -rf /var/lib/apt/lists/*

# Copy and install dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy the graphiti API server
COPY server.py .

# Expose port
EXPOSE 3000

# Run the server
CMD ["python", "server.py"]
