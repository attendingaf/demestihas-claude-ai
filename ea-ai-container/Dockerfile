# EA-AI Containerized Subagent
FROM node:18-alpine

# Install necessary packages
RUN apk add --no-cache \
    python3 \
    py3-pip \
    curl \
    bash

# Set working directory
WORKDIR /app

# Copy package files
COPY package*.json ./

# Install Node dependencies
RUN npm install axios express body-parser cors winston

# Copy application files
COPY . .

# Create directories for state management
RUN mkdir -p /app/state /app/cache /app/logs

# Expose port for HTTP bridge
EXPOSE 8080

# Health check
HEALTHCHECK --interval=30s --timeout=3s --start-period=5s --retries=3 \
  CMD node healthcheck.js || exit 1

# Start the EA-AI server
CMD ["node", "server.js"]
