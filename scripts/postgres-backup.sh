#!/bin/sh
# Copy the database once, then again every 24 hours.
# Files land in /backups. Copies older than 14 days are deleted.
set -eu

: "${POSTGRES_USER:?POSTGRES_USER is required}"
: "${POSTGRES_PASSWORD:?POSTGRES_PASSWORD is required}"
: "${POSTGRES_DB:?POSTGRES_DB is required}"

export PGPASSWORD="$POSTGRES_PASSWORD"
export PGHOST="${POSTGRES_HOST:-db}"

mkdir -p /backups

while true; do
  stamp=$(date -u +%Y%m%dT%H%M%SZ)
  partial="/backups/.tcb-${stamp}.dump.partial"
  outfile="/backups/tcb-${stamp}.dump"

  echo "backup: writing ${outfile}"
  pg_dump -h "$PGHOST" -U "$POSTGRES_USER" -d "$POSTGRES_DB" -Fc -f "$partial"
  mv "$partial" "$outfile"
  touch /backups/.last-ok

  find /backups -name 'tcb-*.dump' -type f -mtime +14 -delete
  echo "backup: saved ${outfile}"

  sleep 86400
done
