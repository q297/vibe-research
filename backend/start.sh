#!/bin/sh
set -e

# Schema first, so the app never starts against an old database
if [ -n "$DATABASE_URL" ]; then
    alembic upgrade head
fi

# The API is reachable only through nginx in the compose network, so its X-Forwarded-For
# is trusted; per-IP login limits would otherwise see the nginx address for everyone
exec uvicorn app.main:app --host 0.0.0.0 --port 8000 --root-path /api \
    --proxy-headers --forwarded-allow-ips "*"
