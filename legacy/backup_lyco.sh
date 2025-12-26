#!/bin/bash
# Lyco.ai Backup Script
BACKUP_DIR='/root/backups'
TIMESTAMP=$(date +%Y%m%d-%H%M%S)

echo 'Starting Lyco.ai backup...'

# Backup code and config
tar -czf $BACKUP_DIR/lyco-code-$TIMESTAMP.tar.gz /root/lyco-ai

# Backup Supabase database if accessible
docker exec supabase-postgres pg_dump -U postgres 2>/dev/null > $BACKUP_DIR/db-$TIMESTAMP.sql || echo 'DB backup skipped'

# Keep only last 7 days of backups
find $BACKUP_DIR -name 'lyco-*' -mtime +7 -delete
find $BACKUP_DIR -name 'db-*' -mtime +7 -delete

echo 'Backup complete: $BACKUP_DIR/lyco-code-$TIMESTAMP.tar.gz'
ls -lh $BACKUP_DIR/*.tar.gz | tail -5
