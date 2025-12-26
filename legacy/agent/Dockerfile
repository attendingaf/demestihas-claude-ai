FROM python:3.10-slim

WORKDIR /app

# Install curl for health checks
RUN apt-get update && \
    apt-get install -y curl && \
    apt-get clean && \
    rm -rf /var/lib/apt/lists/*

# Copy requirements and install dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY main.py .
COPY falkordb_manager.py .
COPY dual_memory_manager.py .
COPY knowledge_tools.py .
COPY initialize_db.py .
COPY document_processor.py .
COPY statefulness_extensions.py .
COPY family_auth.py .
COPY postgres_client.py .
COPY working_memory.py .
COPY social_tools.py .

# Expose FastAPI default port
EXPOSE 8000

# Run FastAPI application
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
