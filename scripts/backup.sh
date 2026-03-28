#!/usr/bin/env bash
set -euo pipefail

# PostgreSQL backup script for clinic CRM
# Usage: ./scripts/backup.sh [backup_dir]
# Designed to be run by cron: 0 2 * * * /opt/clinic-crm/scripts/backup.sh

BACKUP_DIR="${1:-./backups}"
TIMESTAMP=$(date +%Y%m%d_%H%M%S)
BACKUP_FILE="${BACKUP_DIR}/clinic_crm_${TIMESTAMP}.sql.gz"
RETENTION_DAYS=30

mkdir -p "$BACKUP_DIR"

# Dump via docker compose
docker compose exec -T postgres pg_dump -U "${POSTGRES_USER:-clinic}" "${POSTGRES_DB:-clinic_crm}" | gzip > "$BACKUP_FILE"

echo "Backup created: $BACKUP_FILE ($(du -h "$BACKUP_FILE" | cut -f1))"

# Remove backups older than retention period
find "$BACKUP_DIR" -name "clinic_crm_*.sql.gz" -mtime +"$RETENTION_DAYS" -delete
echo "Cleaned backups older than ${RETENTION_DAYS} days"
