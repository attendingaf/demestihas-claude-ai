import winston from 'winston';
import { config } from '../../config/rag-config.js';
import sqliteClient from '../core/sqlite-client-optimized.js';
import projectContextManager from '../context/project-context-manager.js';
import contextPrioritizer from '../context/context-prioritizer.js';
import syncEngine from '../sync/sync-engine.js';

const logger = winston.createLogger({
  level: config.logging.level,
  format: winston.format.json(),
  transports: [
    new winston.transports.Console(),
    new winston.transports.File({ filename: config.logging.file })
  ]
});

class PerformanceMonitor {
  constructor() {
    this.metrics = {
      retrieval: {
        times: [],
        avg: 0,
        p50: 0,
        p95: 0,
        p99: 0,
        under100ms: 0,
        total: 0
      },
      cache: {
        hits: 0,
        misses: 0,
        hitRate: 0,
        lruStats: {}
      },
      sync: {
        latency: [],
        avgLatency: 0,
        lastSync: null,
        successRate: 0
      },
      context: {
        switches: [],
        avgSwitchTime: 0,
        isolationChecks: 0,
        isolationViolations: 0
      },
      system: {
        memoryUsage: [],
        cpuUsage: [],
        dbSize: 0,
        cacheSize: 0
      }
    };
    
    this.alerts = [];
    this.thresholds = {
      retrievalTime: 100, // ms
      cacheHitRate: 0.8,
      syncLatency: 1000, // ms
      contextSwitchTime: 100, // ms
      memoryLimit: 500 * 1024 * 1024 // 500MB
    };
    
    this.monitoringInterval = null;
    this.reportingInterval = null;
  }

  async initialize() {
    try {
      // Start monitoring
      this.startMonitoring();
      
      // Start reporting
      this.startReporting();
      
      logger.info('Performance Monitor initialized');
    } catch (error) {
      logger.error('Failed to initialize Performance Monitor', { 
        error: error.message 
      });
      throw error;
    }
  }

  trackRetrievalTime(time, source = 'unknown') {
    this.metrics.retrieval.times.push({
      time,
      source,
      timestamp: Date.now()
    });
    
    // Keep only last 1000 measurements
    if (this.metrics.retrieval.times.length > 1000) {
      this.metrics.retrieval.times.shift();
    }
    
    // Update statistics
    this.updateRetrievalStats();
    
    // Check threshold
    if (time > this.thresholds.retrievalTime) {
      this.addAlert('HIGH_RETRIEVAL_TIME', {
        time,
        source,
        threshold: this.thresholds.retrievalTime
      });
    }
    
    // Track sub-100ms achievement
    if (time < 100) {
      this.metrics.retrieval.under100ms++;
    }
    this.metrics.retrieval.total++;
  }

  updateRetrievalStats() {
    const times = this.metrics.retrieval.times.map(t => t.time);
    
    if (times.length === 0) return;
    
    // Calculate average
    this.metrics.retrieval.avg = times.reduce((a, b) => a + b, 0) / times.length;
    
    // Calculate percentiles
    const sorted = [...times].sort((a, b) => a - b);
    this.metrics.retrieval.p50 = this.percentile(sorted, 50);
    this.metrics.retrieval.p95 = this.percentile(sorted, 95);
    this.metrics.retrieval.p99 = this.percentile(sorted, 99);
  }

  percentile(sortedArray, p) {
    const index = Math.ceil((p / 100) * sortedArray.length) - 1;
    return sortedArray[Math.max(0, index)];
  }

  async updateCacheMetrics() {
    // Get cache stats from SQLite client
    const sqliteMetrics = await sqliteClient.getPerformanceMetrics();
    
    this.metrics.cache.lruStats = sqliteMetrics.cacheStats;
    
    // Calculate overall hit rate
    let totalHits = 0;
    let totalRequests = 0;
    
    for (const cache of Object.values(sqliteMetrics.cacheStats)) {
      totalHits += cache.hits;
      totalRequests += cache.hits + cache.misses;
    }
    
    this.metrics.cache.hits = totalHits;
    this.metrics.cache.misses = totalRequests - totalHits;
    this.metrics.cache.hitRate = totalRequests > 0 ? (totalHits / totalRequests) : 0;
    
    // Check threshold
    if (this.metrics.cache.hitRate < this.thresholds.cacheHitRate && totalRequests > 50) {
      this.addAlert('LOW_CACHE_HIT_RATE', {
        hitRate: this.metrics.cache.hitRate,
        threshold: this.thresholds.cacheHitRate
      });
    }
  }

  async updateSyncMetrics() {
    const syncMetrics = await syncEngine.getMetrics();
    
    this.metrics.sync.latency = syncMetrics.recentSyncTimes || [];
    this.metrics.sync.avgLatency = syncMetrics.avgSyncTime || 0;
    this.metrics.sync.lastSync = syncMetrics.lastSyncTime;
    this.metrics.sync.successRate = syncMetrics.totalSyncs > 0 ? 
      (syncMetrics.successfulSyncs / syncMetrics.totalSyncs) : 0;
    
    // Check threshold
    if (this.metrics.sync.avgLatency > this.thresholds.syncLatency) {
      this.addAlert('HIGH_SYNC_LATENCY', {
        latency: this.metrics.sync.avgLatency,
        threshold: this.thresholds.syncLatency
      });
    }
  }

  async updateContextMetrics() {
    const contextMetrics = await projectContextManager.getMetrics();
    
    this.metrics.context.switches = contextMetrics.recentSwitchTimes || [];
    this.metrics.context.avgSwitchTime = contextMetrics.avgSwitchTime || 0;
    
    // Check threshold
    if (this.metrics.context.avgSwitchTime > this.thresholds.contextSwitchTime) {
      this.addAlert('SLOW_CONTEXT_SWITCH', {
        switchTime: this.metrics.context.avgSwitchTime,
        threshold: this.thresholds.contextSwitchTime
      });
    }
  }

  async updateSystemMetrics() {
    // Get memory usage
    const memUsage = process.memoryUsage();
    this.metrics.system.memoryUsage.push({
      rss: memUsage.rss,
      heapUsed: memUsage.heapUsed,
      heapTotal: memUsage.heapTotal,
      external: memUsage.external,
      timestamp: Date.now()
    });
    
    // Keep only last 100 measurements
    if (this.metrics.system.memoryUsage.length > 100) {
      this.metrics.system.memoryUsage.shift();
    }
    
    // Check memory threshold
    if (memUsage.rss > this.thresholds.memoryLimit) {
      this.addAlert('HIGH_MEMORY_USAGE', {
        usage: memUsage.rss,
        threshold: this.thresholds.memoryLimit
      });
    }
    
    // Get CPU usage
    const cpuUsage = process.cpuUsage();
    this.metrics.system.cpuUsage.push({
      user: cpuUsage.user,
      system: cpuUsage.system,
      timestamp: Date.now()
    });
    
    // Keep only last 100 measurements
    if (this.metrics.system.cpuUsage.length > 100) {
      this.metrics.system.cpuUsage.shift();
    }
    
    // Get database stats
    const dbStats = await sqliteClient.getStats();
    this.metrics.system.dbSize = dbStats.memories + dbStats.patterns + dbStats.embeddings;
    this.metrics.system.cacheSize = dbStats.contextCache || 0;
  }

  checkContextIsolation(projectId, accessedData) {
    this.metrics.context.isolationChecks++;
    
    // Check if accessed data belongs to the correct project
    for (const item of accessedData) {
      if (item.project_id && item.project_id !== projectId) {
        this.metrics.context.isolationViolations++;
        
        this.addAlert('CONTEXT_ISOLATION_VIOLATION', {
          expectedProject: projectId,
          actualProject: item.project_id,
          itemId: item.id
        });
        
        return false;
      }
    }
    
    return true;
  }

  addAlert(type, details) {
    const alert = {
      type,
      details,
      timestamp: Date.now(),
      resolved: false
    };
    
    this.alerts.push(alert);
    
    // Keep only last 100 alerts
    if (this.alerts.length > 100) {
      this.alerts.shift();
    }
    
    // Log critical alerts
    if (type.includes('VIOLATION') || type.includes('HIGH')) {
      logger.warn('Performance alert', alert);
    }
    
    return alert;
  }

  async startMonitoring() {
    // Update metrics every 10 seconds
    this.monitoringInterval = setInterval(async () => {
      try {
        await this.updateCacheMetrics();
        await this.updateSyncMetrics();
        await this.updateContextMetrics();
        await this.updateSystemMetrics();
      } catch (error) {
        logger.error('Error updating metrics', { error: error.message });
      }
    }, 10000);
    
    // Initial update
    setTimeout(async () => {
      await this.updateCacheMetrics();
      await this.updateSyncMetrics();
      await this.updateContextMetrics();
      await this.updateSystemMetrics();
    }, 1000);
  }

  startReporting() {
    // Generate report every minute
    this.reportingInterval = setInterval(() => {
      this.generateReport();
    }, 60000);
  }

  generateReport() {
    const report = {
      timestamp: Date.now(),
      retrieval: {
        avgTime: this.metrics.retrieval.avg,
        p95Time: this.metrics.retrieval.p95,
        p99Time: this.metrics.retrieval.p99,
        under100msRate: this.metrics.retrieval.total > 0 ? 
          (this.metrics.retrieval.under100ms / this.metrics.retrieval.total) : 0,
        targetMet: this.metrics.retrieval.avg < 100
      },
      cache: {
        hitRate: this.metrics.cache.hitRate,
        targetMet: this.metrics.cache.hitRate > 0.8
      },
      sync: {
        avgLatency: this.metrics.sync.avgLatency,
        successRate: this.metrics.sync.successRate,
        targetMet: this.metrics.sync.avgLatency < 1000
      },
      context: {
        avgSwitchTime: this.metrics.context.avgSwitchTime,
        isolationViolations: this.metrics.context.isolationViolations,
        targetMet: this.metrics.context.avgSwitchTime < 100 && 
                   this.metrics.context.isolationViolations === 0
      },
      system: {
        memoryUsage: this.metrics.system.memoryUsage.length > 0 ? 
          this.metrics.system.memoryUsage[this.metrics.system.memoryUsage.length - 1] : null,
        dbSize: this.metrics.system.dbSize,
        cacheSize: this.metrics.system.cacheSize
      },
      recentAlerts: this.alerts.filter(a => !a.resolved).slice(-10),
      overallHealth: this.calculateOverallHealth()
    };
    
    // Log summary
    logger.info('Performance Report', {
      retrievalAvg: report.retrieval.avgTime.toFixed(2) + 'ms',
      cacheHitRate: (report.cache.hitRate * 100).toFixed(1) + '%',
      syncLatency: report.sync.avgLatency.toFixed(2) + 'ms',
      contextSwitch: report.context.avgSwitchTime.toFixed(2) + 'ms',
      health: report.overallHealth
    });
    
    // Log detailed report if performance is degraded
    if (report.overallHealth !== 'GOOD') {
      logger.warn('Performance degradation detected', report);
    }
    
    return report;
  }

  calculateOverallHealth() {
    let issues = 0;
    
    if (this.metrics.retrieval.avg > 100) issues++;
    if (this.metrics.cache.hitRate < 0.8) issues++;
    if (this.metrics.sync.avgLatency > 1000) issues++;
    if (this.metrics.context.avgSwitchTime > 100) issues++;
    if (this.metrics.context.isolationViolations > 0) issues++;
    
    const unresolvedAlerts = this.alerts.filter(a => !a.resolved).length;
    if (unresolvedAlerts > 5) issues++;
    
    if (issues === 0) return 'GOOD';
    if (issues <= 2) return 'DEGRADED';
    return 'CRITICAL';
  }

  async getMetrics() {
    return {
      ...this.metrics,
      alerts: this.alerts.filter(a => !a.resolved),
      thresholds: this.thresholds,
      health: this.calculateOverallHealth()
    };
  }

  async getDetailedReport() {
    const report = this.generateReport();
    
    // Add detailed breakdowns
    report.retrieval.histogram = this.generateHistogram(
      this.metrics.retrieval.times.map(t => t.time),
      [0, 50, 100, 200, 500, 1000]
    );
    
    report.cache.breakdown = this.metrics.cache.lruStats;
    
    report.sync.timeline = this.metrics.sync.latency.map((time, i) => ({
      time,
      index: i,
      timestamp: Date.now() - (this.metrics.sync.latency.length - i) * 60000
    }));
    
    report.system.memoryTrend = this.calculateTrend(
      this.metrics.system.memoryUsage.map(m => m.rss)
    );
    
    return report;
  }

  generateHistogram(values, buckets) {
    const histogram = {};
    
    for (const bucket of buckets) {
      histogram[`<${bucket}ms`] = 0;
    }
    histogram[`>${buckets[buckets.length - 1]}ms`] = 0;
    
    for (const value of values) {
      let placed = false;
      
      for (const bucket of buckets) {
        if (value < bucket) {
          histogram[`<${bucket}ms`]++;
          placed = true;
          break;
        }
      }
      
      if (!placed) {
        histogram[`>${buckets[buckets.length - 1]}ms`]++;
      }
    }
    
    return histogram;
  }

  calculateTrend(values) {
    if (values.length < 2) return 'STABLE';
    
    const recent = values.slice(-10);
    const older = values.slice(-20, -10);
    
    if (older.length === 0) return 'STABLE';
    
    const recentAvg = recent.reduce((a, b) => a + b, 0) / recent.length;
    const olderAvg = older.reduce((a, b) => a + b, 0) / older.length;
    
    const change = (recentAvg - olderAvg) / olderAvg;
    
    if (change > 0.2) return 'INCREASING';
    if (change < -0.2) return 'DECREASING';
    return 'STABLE';
  }

  setThreshold(metric, value) {
    if (this.thresholds.hasOwnProperty(metric)) {
      this.thresholds[metric] = value;
      logger.info('Threshold updated', { metric, value });
    }
  }

  resolveAlert(alertId) {
    const alert = this.alerts.find(a => a.timestamp === alertId);
    if (alert) {
      alert.resolved = true;
    }
  }

  reset() {
    // Reset all metrics
    this.metrics = {
      retrieval: {
        times: [],
        avg: 0,
        p50: 0,
        p95: 0,
        p99: 0,
        under100ms: 0,
        total: 0
      },
      cache: {
        hits: 0,
        misses: 0,
        hitRate: 0,
        lruStats: {}
      },
      sync: {
        latency: [],
        avgLatency: 0,
        lastSync: null,
        successRate: 0
      },
      context: {
        switches: [],
        avgSwitchTime: 0,
        isolationChecks: 0,
        isolationViolations: 0
      },
      system: {
        memoryUsage: [],
        cpuUsage: [],
        dbSize: 0,
        cacheSize: 0
      }
    };
    
    this.alerts = [];
    
    logger.info('Performance metrics reset');
  }

  stop() {
    if (this.monitoringInterval) {
      clearInterval(this.monitoringInterval);
    }
    
    if (this.reportingInterval) {
      clearInterval(this.reportingInterval);
    }
    
    // Generate final report
    this.generateReport();
    
    logger.info('Performance Monitor stopped');
  }
}

export default new PerformanceMonitor();