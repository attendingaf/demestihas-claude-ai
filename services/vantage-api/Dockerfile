FROM node:20-slim

WORKDIR /app

COPY package*.json ./
RUN npm install

COPY . .
RUN npm run build

# Expose port
EXPOSE 3005

# Start command
CMD ["npm", "start"]
