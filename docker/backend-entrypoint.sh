#!/bin/sh
set -e

if [ "${RUN_MIGRATIONS:-0}" = "1" ]; then
  python -m app.scripts.prepare_migrations
  alembic upgrade head
fi

if [ "${SEED_ADMIN:-0}" = "1" ]; then
  python -m app.scripts.init_admin
fi

exec "$@"
