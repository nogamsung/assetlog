#!/bin/sh
# Container entrypoint — apply schema migrations before handing off to
# whatever CMD the image was started with (uvicorn by default).
#
# Without this step, a new image carrying a Transaction column the DB
# doesn't have yet (e.g. fee, see PR #189) silently rolls out and every
# PDF import crashes at INSERT time with "Unknown column". Running the
# migration on every start is idempotent — alembic exits 0 immediately
# if the DB is already at head.
#
# To skip (e.g. read-only replicas, CI jobs), set SKIP_DB_MIGRATIONS=1.

set -e

if [ "${SKIP_DB_MIGRATIONS:-0}" = "1" ]; then
  echo "[entrypoint] SKIP_DB_MIGRATIONS=1 — skipping alembic upgrade head"
else
  echo "[entrypoint] alembic upgrade head"
  alembic upgrade head
fi

exec "$@"
