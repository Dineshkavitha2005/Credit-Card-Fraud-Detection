#!/usr/bin/env bash
# ==============================================================================
# Sentinel PostgreSQL Safe Database Restoration Script
# Requires explicit file path argument and user confirmation.
# ==============================================================================

set -euo pipefail

if [ "$#" -ne 1 ]; then
    echo "Usage: $0 <path-to-backup-file.sql.gz>"
    exit 1
fi

BACKUP_FILE="$1"
CONTAINER_NAME="${DB_CONTAINER:-fraud_detection_postgres}"
DB_USER="${POSTGRES_USER:-fraud_user}"
DB_NAME="${POSTGRES_DB:-fraud_db}"

if [ ! -f "${BACKUP_FILE}" ]; then
    echo "ERROR: Backup file does not exist: ${BACKUP_FILE}" >&2
    exit 1
fi

echo "======================================================================"
echo "⚠️  CRITICAL: SENTINEL DATABASE RESTORATION"
echo "======================================================================"
echo "Target Container: ${CONTAINER_NAME}"
echo "Target Database:  ${DB_NAME}"
echo "Source File:      ${BACKUP_FILE}"
echo "This operation will overwrite existing tables in the database!"
echo "======================================================================"

read -p "Are you sure you want to proceed with database restore? (yes/no): " -r CONFIRM
if [ "${CONFIRM}" != "yes" ]; then
    echo "Restoration cancelled by user."
    exit 0
fi

echo "Extracting and restoring database..."
gunzip -c "${BACKUP_FILE}" | docker exec -i "${CONTAINER_NAME}" psql -U "${DB_USER}" -d "${DB_NAME}"

echo "✅ Database restored successfully from ${BACKUP_FILE}."
