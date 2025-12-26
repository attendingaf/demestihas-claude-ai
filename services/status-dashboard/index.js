import express from 'express';
import axios from 'axios';
import { createClient } from 'redis';
import path from 'path';
import { fileURLToPath } from 'url';

const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);

const app = express();
const PORT = process.env.PORT || 9999;

// Parse services configuration from environment
const SERVICES = JSON.parse(process.env.SERVICES_CONFIG || '[]');

// Redis client for checking Redis health
let redisClient;

// Service status cache
const statusCache = new Map();

// Initialize Redis connection
async function initRedis() {
    try {
        redisClient = createClient({
            socket: {
                host: process.env.REDIS_HOST || 'redis',
                port: parseInt(process.env.REDIS_PORT || '6379')
            }
        });

        redisClient.on('error', (err) => {
            console.error('Redis Client Error:', err);
        });

        await redisClient.connect();
        console.log('Connected to Redis');
    } catch (error) {
        console.error('Failed to connect to Redis:', error);
    }
}

// Check individual service health
async function checkServiceHealth(service) {
    const startTime = Date.now();

    try {
        if (service.type === 'redis') {
            // Special handling for Redis
            if (!redisClient || !redisClient.isOpen) {
                throw new Error('Redis client not connected');
            }

            const pong = await redisClient.ping();
            const info = await redisClient.info('server');
            const uptimeMatch = info.match(/uptime_in_seconds:(\d+)/);
            const uptime = uptimeMatch ? parseInt(uptimeMatch[1]) : 0;

            return {
                status: 'healthy',
                responseTime: Date.now() - startTime,
                details: {
                    uptime: `${Math.floor(uptime / 3600)}h ${Math.floor((uptime % 3600) / 60)}m`,
                    ping: pong
                }
            };
        } else {
            // HTTP health check for other services
            const response = await axios.get(service.url, {
                timeout: 5000,
                validateStatus: () => true
            });

            const isHealthy = response.status === 200;
            const responseTime = Date.now() - startTime;

            return {
                status: isHealthy ? 'healthy' : 'unhealthy',
                responseTime,
                statusCode: response.status,
                details: response.data || {}
            };
        }
    } catch (error) {
        return {
            status: 'error',
            responseTime: Date.now() - startTime,
            error: error.message
        };
    }
}

// Check all services
async function checkAllServices() {
    const results = {};

    for (const service of SERVICES) {
        const health = await checkServiceHealth(service);
        results[service.name] = {
            ...health,
            port: service.port,
            lastChecked: new Date().toISOString()
        };
        statusCache.set(service.name, results[service.name]);
    }

    return results;
}

// Middleware
app.use(express.json());
app.use(express.static(path.join(__dirname, 'public')));

// Health endpoint for the dashboard itself
app.get('/health', (req, res) => {
    res.json({
        service: 'status-dashboard',
        status: 'healthy',
        uptime: process.uptime(),
        timestamp: new Date().toISOString()
    });
});

// API endpoint to get all service statuses
app.get('/api/status', async (req, res) => {
    try {
        const statuses = await checkAllServices();
        res.json({
            timestamp: new Date().toISOString(),
            services: statuses
        });
    } catch (error) {
        res.status(500).json({
            error: 'Failed to check service statuses',
            message: error.message
        });
    }
});

// API endpoint to get cached statuses (faster)
app.get('/api/status/cached', (req, res) => {
    const statuses = {};
    statusCache.forEach((value, key) => {
        statuses[key] = value;
    });

    res.json({
        timestamp: new Date().toISOString(),
        services: statuses,
        cached: true
    });
});

// API endpoint to get specific service status
app.get('/api/status/:serviceName', async (req, res) => {
    const serviceName = req.params.serviceName;
    const service = SERVICES.find(s => s.name.toLowerCase() === serviceName.toLowerCase());

    if (!service) {
        return res.status(404).json({ error: 'Service not found' });
    }

    try {
        const health = await checkServiceHealth(service);
        res.json({
            service: service.name,
            ...health,
            port: service.port,
            timestamp: new Date().toISOString()
        });
    } catch (error) {
        res.status(500).json({
            error: 'Failed to check service status',
            message: error.message
        });
    }
});

// Start periodic health checks
setInterval(async () => {
    try {
        await checkAllServices();
        console.log('Health check completed at', new Date().toISOString());
    } catch (error) {
        console.error('Health check failed:', error);
    }
}, 10000); // Check every 10 seconds

// Initialize and start server
async function start() {
    await initRedis();

    // Initial health check
    await checkAllServices();

    app.listen(PORT, '0.0.0.0', () => {
        console.log(`Status Dashboard running on http://localhost:${PORT}`);
        console.log('Monitoring services:', SERVICES.map(s => s.name).join(', '));
    });
}

start().catch(console.error);
