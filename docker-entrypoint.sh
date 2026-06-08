#!/usr/bin/env bash
set -euo pipefail

# Wait for MySQL to be ready before running migrations.
MYSQL_HOST="${MYSQL_HOST:-mysql}"
echo "Waiting for MySQL at ${MYSQL_HOST}:3306 …"
until python -c "import socket; socket.create_connection(('${MYSQL_HOST}', 3306), timeout=2)" 2>/dev/null; do
  sleep 1
done
echo "MySQL is up."

# Bootstrap (migrate + seed + collectstatic) runs in EXACTLY ONE container.
# The compose stack runs both ``web`` (gunicorn) and ``worker`` (qcluster)
# from this same image, and both ``depends_on: mysql: service_healthy`` —
# so without a gate they both race to ``CREATE TABLE django_migrations`` and
# whichever loses the race crashes with "already exists", restarts under
# ``restart: unless-stopped``, and the stack loops.
#
# ``--fake-initial`` is added defensively: if a deployed server's
# ``django_migrations`` ever loses sync with the actual schema (e.g. a
# SQL dump was loaded out-of-band), Django will mark initial migrations
# applied where the tables already match, then run the rest normally.
# On a fresh DB the flag is a no-op.
if [[ "${1:-}" == "gunicorn" ]]; then
  python manage.py migrate --noinput --fake-initial
  python manage.py seed_all
  python manage.py collectstatic --noinput
fi

# Hand off to whatever was passed as CMD (gunicorn, qcluster, etc.).
exec "$@"
