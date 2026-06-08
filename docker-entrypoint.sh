#!/usr/bin/env bash
set -euo pipefail

# Wait for MySQL to be ready before running migrations.
MYSQL_HOST="${MYSQL_HOST:-mysql}"
echo "Waiting for MySQL at ${MYSQL_HOST}:3306 …"
until python -c "import socket; socket.create_connection(('${MYSQL_HOST}', 3306), timeout=2)" 2>/dev/null; do
  sleep 1
done
echo "MySQL is up."

# Apply migrations. Safe to run repeatedly.
python manage.py migrate --noinput

# Hand off to whatever was passed as CMD (gunicorn, qcluster, etc.).
exec "$@"
