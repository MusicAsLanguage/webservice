#!/bin/bash
set -e

echo "Starting SSH ..."
service ssh start

cd /app
exec gunicorn --bind 0.0.0.0:8000 --workers "${WEB_CONCURRENCY:-1}" \
    --worker-class gthread --threads 4 --timeout 180 \
    --access-logfile - --error-logfile - wsgi:app
