#!/bin/sh
set -eu

python - <<'PY'
import os, socket, time
from urllib.parse import urlparse

def wait(host, port, label, seconds=60):
    deadline = time.time() + seconds
    while time.time() < deadline:
        try:
            with socket.create_connection((host, port), timeout=2):
                return
        except OSError:
            time.sleep(1)
    raise SystemExit(f"{label} {host}:{port} did not become ready")

host = os.environ.get("DB_HOST", "db")
port = int(os.environ.get("DB_PORT", "5432"))
wait(host, port, "database")

redis_url = (os.environ.get("REDIS_URL") or "").strip()
if redis_url:
    parsed = urlparse(redis_url)
    if parsed.hostname:
        wait(parsed.hostname, parsed.port or 6379, "redis")
PY

python manage.py migrate --noinput
python manage.py collectstatic --noinput
exec "$@"
