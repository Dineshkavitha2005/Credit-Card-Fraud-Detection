#!/usr/bin/env bash
# ==============================================================================
# Sentinel PostgreSQL Automated Backup Script
# Creates compressed, timestamped database dumps with retention management.
# ==============================================================================

set -euo pipefail

BACKUP_DIR="${BACKUP_DIR:-./instance/backups}"
TIMESTAMP="$(date +'%Y%m%d_%H%M%S')"
BACKUP_FILE="${BACKUP_DIR}/sentinel_db_${TIMESTAMP}.sql.gz"
LOG_FILE="${BACKUP_DIR}/backup.log"
RETENTION_DAYS="${RETENTION_DAYS:-30}"

CONTAINER_NAME="${DB_CONTAINER:-fraud_detection_postgres}"
DB_USER="${POSTGRES_USER:-fraud_user}"
DB_NAME="${POSTGRES_DB:-fraud_db}"

mkdir -p "${BACKUP_DIR}"

log() {
    echo "[$(date +'%Y-%m-%d %H:%M:%S')] $1" | tee -a "${LOG_FILE}"
}

log "Starting Sentinel PostgreSQL database backup..."

if ! docker ps --format '{{.Names}}' | grep -q "^${CONTAINER_NAME}$"; then
    log "ERROR: Container ${CONTAINER_NAME} is not running. Aborting backup." >&2
    exit 1
fi

log "Executing pg_dump inside container ${CONTAINER_NAME}..."
if docker exec -t "${CONTAINER_NAME}" pg_dump -U "${DB_USER}" -d "${DB_NAME}" --clean --if-exists | gzip > "${BACKUP_FILE}"; then
    BACKUP_SIZE="$(du -h "${BACKUP_FILE}" | cut -f1)"
    log "SUCCESS: Backup completed successfully: ${BACKUP_FILE} (Size: ${BACKUP_SIZE})"
else
    log "ERROR: pg_dump execution failed!" >&2
    rm -f "${BACKUP_FILE}"
    exit 1
fi

# Retention policy: remove backups older than RETENTION_DAYS
log "Purging backups older than ${RETENTION_DAYS} days..."
find "${BACKUP_DIR}" -type f -name "sentinel_db_*.sql.gz" -mtime +"${RETENTION_DAYS}" -exec rm -vf {} \; | while read -r removed; do
    log "Removed expired backup: ${removed}"
done

log "Backup operation finished."
