import winston from 'winston';
import { config } from '../../config/rag-config.js';
import originalClient from './sqlite-client.js';
import optimizedClient from './sqlite-client-optimized.js';

const logger = winston.createLogger({
  level: config.logging.level,
  format: winston.format.json(),
  transports: [
    new winston.transports.Console(),
    new winston.transports.File({ filename: config.logging.file })
  ]
});

class SQLiteMigration {
  constructor() {
    this.migrationComplete = false;
  }

  async migrate() {
    logger.info('Starting SQLite client migration to optimized version...');
    
    try {
      // Initialize both clients
      await originalClient.initialize();
      await optimizedClient.initialize();
      
      // Create project_settings table if it doesn't exist
      await this.createProjectSettingsTable();
      
      // Migrate existing data to optimized format
      await this.migrateExistingData();
      
      // Verify migration
      await this.verifyMigration();
      
      this.migrationComplete = true;
      logger.info('SQLite migration completed successfully');
      
      return true;
    } catch (error) {
      logger.error('SQLite migration failed', { error: error.message });
      throw error;
    }
  }

  async createProjectSettingsTable() {
    const sql = `
      CREATE TABLE IF NOT EXISTS project_settings (
        project_id TEXT PRIMARY KEY,
        settings TEXT NOT NULL,
        updated_at INTEGER DEFAULT (strftime('%s', 'now'))
      )
    `;
    
    try {
      await optimizedClient.db.exec(sql);
      logger.info('Project settings table created');
    } catch (error) {
      logger.error('Failed to create project settings table', { error: error.message });
      throw error;
    }
  }

  async migrateExistingData() {
    logger.info('Migrating existing data to optimized indexes...');
    
    try {
      // Reindex for better performance
      await optimizedClient.db.exec('ANALYZE');
      await optimizedClient.db.exec('VACUUM');
      
      // Update statistics
      await optimizedClient.db.exec('PRAGMA optimize');
      
      logger.info('Data migration and optimization complete');
    } catch (error) {
      logger.error('Failed to migrate existing data', { error: error.message });
      throw error;
    }
  }

  async verifyMigration() {
    const checks = [];
    
    // Check context_cache table
    const contextCacheCheck = await optimizedClient.db.get(
      "SELECT COUNT(*) as count FROM sqlite_master WHERE type='table' AND name='context_cache'"
    );
    checks.push({
      name: 'Context cache table',
      passed: contextCacheCheck.count === 1
    });
    
    // Check indexes
    const indexCheck = await optimizedClient.db.all(
      "SELECT name FROM sqlite_master WHERE type='index' AND name LIKE 'idx_%'"
    );
    checks.push({
      name: 'Performance indexes',
      passed: indexCheck.length >= 5
    });
    
    // Check memory mapping
    const mmapCheck = await optimizedClient.db.get('PRAGMA mmap_size');
    checks.push({
      name: 'Memory mapping',
      passed: mmapCheck.mmap_size > 0
    });
    
    // Check project settings table
    const settingsCheck = await optimizedClient.db.get(
      "SELECT COUNT(*) as count FROM sqlite_master WHERE type='table' AND name='project_settings'"
    );
    checks.push({
      name: 'Project settings table',
      passed: settingsCheck.count === 1
    });
    
    // Log results
    for (const check of checks) {
      if (check.passed) {
        logger.info(`✅ ${check.name} verified`);
      } else {
        logger.error(`❌ ${check.name} failed`);
        throw new Error(`Migration verification failed: ${check.name}`);
      }
    }
    
    return true;
  }

  async rollback() {
    logger.warn('Rolling back SQLite migration...');
    
    try {
      // Close optimized client
      await optimizedClient.close();
      
      // Continue using original client
      this.migrationComplete = false;
      
      logger.info('Rollback completed, using original SQLite client');
    } catch (error) {
      logger.error('Rollback failed', { error: error.message });
      throw error;
    }
  }
}

export default new SQLiteMigration();