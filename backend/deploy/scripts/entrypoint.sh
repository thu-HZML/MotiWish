#!/bin/sh
set -e

if [ -n "$POSTGRES_HOST" ]; then
  echo "Waiting for PostgreSQL at ${POSTGRES_HOST}:${POSTGRES_PORT:-5432}..."
  until python -c "import socket; socket.create_connection(('${POSTGRES_HOST}', int('${POSTGRES_PORT:-5432}')), timeout=3).close()"; do
    sleep 1
  done
fi

if [ "${SKIP_DJANGO_STARTUP_TASKS:-false}" != "true" ]; then
  python manage.py migrate --noinput
  python manage.py collectstatic --noinput
fi

exec "$@"
