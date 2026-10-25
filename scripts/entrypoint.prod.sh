#!/bin/sh
# Start as root so a fresh media volume can be given to the django user,
# then drop privileges before migrations and gunicorn.
set -eu

mkdir -p /app/media /app/staticfiles /app/cache
chown -R django:django /app/media /app/staticfiles /app/cache

exec gosu django "$@"
