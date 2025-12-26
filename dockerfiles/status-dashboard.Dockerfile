FROM node:20-alpine

# Install curl for healthcheck
RUN apk add --no-cache curl

WORKDIR /app

# Copy package files
COPY package*.json ./

# Install dependencies
RUN npm install --omit=dev

# Copy application files
COPY . .

# Create logs directory
RUN mkdir -p /app/logs

# Expose port
EXPOSE 9999

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=20s --retries=3 \
    CMD curl -f http://localhost:9999/health || exit 1

# Start the server
CMD ["node", "index.js"]
