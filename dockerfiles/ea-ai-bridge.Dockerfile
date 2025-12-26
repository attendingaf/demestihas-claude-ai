FROM node:20-alpine

# Install curl for healthcheck
RUN apk add --no-cache curl

WORKDIR /app

# Copy package files from ea-ai-container
COPY package*.json ./

# Install dependencies
RUN npm install --omit=dev

# Copy application files
COPY *.js ./

# Create necessary directories
RUN mkdir -p /app/logs /app/cache /app/state

# Expose port
EXPOSE 8080

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=15s --retries=3 \
    CMD curl -f http://localhost:8080/health || exit 1

# Start the server
CMD ["node", "server.js"]
