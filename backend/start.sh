#!/bin/sh
set -e

# Schema first, so the app never starts against an old database
if [ -n "$DATABASE_URL" ]; then
    alembic upgrade head
fi

exec uvicorn app.main:app --host 0.0.0.0 --port 8000 --proxy-headers --root-path /api
