#!/bin/sh
set -eu

python - <<'PY'
import os, socket, time

host = os.environ.get("DB_HOST", "db")
port = int(os.environ.get("DB_PORT", "5432"))
deadline = time.time() + 60
while time.time() < deadline:
    try:
        with socket.create_connection((host, port), timeout=2):
            break
    except OSError:
        time.sleep(1)
else:
    raise SystemExit(f"database {host}:{port} did not become ready")
PY

python manage.py migrate --noinput
exec "$@"
