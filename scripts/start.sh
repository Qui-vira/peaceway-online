#!/bin/sh
# Shared Railway/Procfile entrypoint. The web service and the scheduler worker
# both deploy this repo and share railway.json, so branch on PW_ROLE:
#   PW_ROLE=worker -> scheduler worker (app.worker_app; no migrations)
#   unset          -> web API (run migrations, then app.main)
# Both serve /health, so the platform health-check passes for either role.
set -e

if [ "$PW_ROLE" = "worker" ]; then
  exec uvicorn app.worker_app:app --host 0.0.0.0 --port "$PORT"
fi

alembic upgrade head
exec uvicorn app.main:app --host 0.0.0.0 --port "$PORT"
