#!/bin/sh
# restore.sh — восстановление из локальных бекапов
set -e

BACKUP_DIR=/backups
RESTORE_TIMESTAMP=$1   # например, 20260505_020000

if [ -z "$RESTORE_TIMESTAMP" ]; then
    echo "Usage: restore.sh <timestamp>   # find in ./backups directory"
    exit 1
fi

echo "=== Restoring from backups with timestamp ${RESTORE_TIMESTAMP} ==="

# 1. PostgreSQL
echo "Restoring PostgreSQL..."
docker compose down backend   # останавливаем приложение
docker compose up -d postgres
sleep 5
docker exec -i postgres pg_restore -U "${POSTGRES_USER}" -d "${POSTGRES_DB}" --clean --if-exists < "${BACKUP_DIR}/postgres_${RESTORE_TIMESTAMP}.dump"
echo "PostgreSQL restored."

# 2. MinIO
echo "Restoring MinIO data..."
docker compose stop minio
rm -rf ./.docker/minio-data/*
tar -xzf "${BACKUP_DIR}/minio_${RESTORE_TIMESTAMP}.tar.gz" -C ./.docker/minio-data/
docker compose start minio
echo "MinIO restored."

# Запускаем backend
docker compose up -d backend
echo "=== Restore completed. ==="
