#!/bin/bash

# Database Backup Script for Local AI Agent
# Can be run manually or scheduled as a cron job

set -euo pipefail

# Configuration
BACKUP_DIR=${BACKUP_DIR:-"/backups"}
DATABASE_HOST=${DATABASE_HOST:-"postgres"}
DATABASE_PORT=${DATABASE_PORT:-"5432"}
DATABASE_NAME=${DATABASE_NAME:-"ai_agent_db"}
DATABASE_USER=${DATABASE_USER:-"aiagent"}
RETENTION_DAYS=${BACKUP_RETENTION_DAYS:-30}
TIMESTAMP=$(date +"%Y%m%d_%H%M%S")
BACKUP_FILE="$BACKUP_DIR/ai_agent_backup_$TIMESTAMP.sql"
COMPRESSED_BACKUP="$BACKUP_FILE.gz"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

log() {
    echo -e "${GREEN}[$(date +'%Y-%m-%d %H:%M:%S')] $1${NC}"
}

warn() {
    echo -e "${YELLOW}[WARNING] $1${NC}"
}

error() {
    echo -e "${RED}[ERROR] $1${NC}"
    exit 1
}

# Create backup directory if it doesn't exist
mkdir -p "$BACKUP_DIR"

# Check if database is accessible
log "Checking database connectivity..."
if ! pg_isready -h "$DATABASE_HOST" -p "$DATABASE_PORT" -U "$DATABASE_USER" -d "$DATABASE_NAME"; then
    error "Cannot connect to database at $DATABASE_HOST:$DATABASE_PORT"
fi

# Create database backup
log "Creating database backup..."
if ! pg_dump -h "$DATABASE_HOST" -p "$DATABASE_PORT" -U "$DATABASE_USER" -d "$DATABASE_NAME" \
    --verbose --clean --no-owner --no-privileges > "$BACKUP_FILE"; then
    error "Failed to create database backup"
fi

# Compress backup
log "Compressing backup..."
if ! gzip "$BACKUP_FILE"; then
    error "Failed to compress backup"
fi

# Verify backup
log "Verifying backup..."
if [ ! -f "$COMPRESSED_BACKUP" ]; then
    error "Backup file not found after compression"
fi

BACKUP_SIZE=$(du -h "$COMPRESSED_BACKUP" | cut -f1)
log "Backup created successfully: $COMPRESSED_BACKUP ($BACKUP_SIZE)"

# Cleanup old backups
log "Cleaning up old backups (keeping last $RETENTION_DAYS days)..."
find "$BACKUP_DIR" -name "ai_agent_backup_*.sql.gz" -type f -mtime +$RETENTION_DAYS -delete

# List remaining backups
log "Current backups:"
ls -lh "$BACKUP_DIR"/ai_agent_backup_*.sql.gz 2>/dev/null || log "No backups found"

log "Backup process completed successfully"