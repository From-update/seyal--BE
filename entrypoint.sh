#!/bin/sh
set -e

if [ -n "$DATABASE_URL" ]; then
    echo "Checking database connection..."
    while ! python -c "
import os, sys, urllib.parse, socket
url = urllib.parse.urlparse(os.environ['DATABASE_URL'])
s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
s.settimeout(2)
try:
    s.connect((url.hostname, url.port or 5432))
    s.close()
    sys.exit(0)
except Exception:
    sys.exit(1)
"; do
        echo "Waiting for PostgreSQL database to be ready..."
        sleep 2
    done
    echo "PostgreSQL is ready!"
fi

echo "Applying database migrations..."
python manage.py migrate --noinput

echo "Seeding initial Seyal data..."
python seed_data.py || true

echo "Starting Seyal API service..."
exec "$@"
