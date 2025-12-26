FROM node:20-alpine

# Install curl for healthcheck
RUN apk add --no-cache curl

WORKDIR /app

# Copy package files
COPY package*.json ./

# Install dependencies
RUN npm install --omit=dev

# Copy application files
COPY *.js ./
COPY data ./data/

# Create necessary directories
RUN mkdir -p /app/logs /app/credentials

# Expose port
EXPOSE 7777

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=10s --retries=3 \
    CMD curl -f http://localhost:7777/health || exit 1

# Start the API server
CMD ["node", "memory-api-enhanced.js"]
