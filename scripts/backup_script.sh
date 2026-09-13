#!/bin/sh
set -e

BACKUP_DIR=/backups
TIMESTAMP=$(date +%Y%m%d_%H%M%S)
RETENTION_DAYS=7

# Цветной вывод (не обязательно)
log() { echo "[$(date '+%F %T')] $1"; }

# 1. Бэкап PostgreSQL (логический дамп)
log "Backing up PostgreSQL..."
PGPASSWORD="${POSTGRES_PASSWORD}" pg_dump \
    -h postgres \
    -U "${POSTGRES_USER}" \
    -d "${POSTGRES_DB}" \
    -Fc \
    -f "${BACKUP_DIR}/postgres_${TIMESTAMP}.dump"
log "PostgreSQL dump created: ${BACKUP_DIR}/postgres_${TIMESTAMP}.dump"

# 2. Бэкап MinIO (tar.gz всей папки данных)
log "Backing up MinIO data..."
tar -czf "${BACKUP_DIR}/minio_${TIMESTAMP}.tar.gz" -C /minio_data .
log "MinIO backup created: ${BACKUP_DIR}/minio_${TIMESTAMP}.tar.gz"

# 3. Удаление старых локальных копий
log "Removing backups older than ${RETENTION_DAYS} days..."
find "${BACKUP_DIR}" -type f -mtime +${RETENTION_DAYS} -delete
log "Local cleanup done."

# 4. Отправка в Yandex Object Storage (опционально, если настроены AWS CLI)
if [ ! -z "$AWS_ACCESS_KEY_ID" ]; then
    log "Uploading to Yandex S3..."
    # Устанавливаем AWS CLI (можно предустановить в образе)
    if ! command -v aws &> /dev/null; then
        apk add --no-cache aws-cli
    fi
    aws --endpoint-url "${YANDEX_S3_ENDPOINT}" s3 sync "${BACKUP_DIR}/" "s3://${YANDEX_S3_BUCKET}/latest/" --delete
    # или загружать каждый файл отдельно с меткой даты
    aws --endpoint-url "${YANDEX_S3_ENDPOINT}" s3 cp "${BACKUP_DIR}/postgres_${TIMESTAMP}.dump" "s3://${YANDEX_S3_BUCKET}/daily/postgres_${TIMESTAMP}.dump"
    aws --endpoint-url "${YANDEX_S3_ENDPOINT}" s3 cp "${BACKUP_DIR}/minio_${TIMESTAMP}.tar.gz" "s3://${YANDEX_S3_BUCKET}/daily/minio_${TIMESTAMP}.tar.gz"
    log "Upload complete."
fi

log "Backup finished successfully."