#!/usr/bin/env bash
# Run by the shared python.yml after install, before the checks: CI's mirror of `task db:init`,
# which CI never runs. Creates tvbf and tvbf_test with the app and catalog schemas, which
# Alembic can't create (migrations/env.py filters on them). A schema added or removed here is
# one of the hand-maintained lists in .claude/CLAUDE.md ("Adding a schema...").
set -euo pipefail
export PGPASSWORD=root
psql=(psql -h localhost -U root -v ON_ERROR_STOP=1)
for db in tvbf tvbf_test; do
  "${psql[@]}" -d postgres -c "CREATE DATABASE $db;"
  "${psql[@]}" -d "$db" -c "CREATE SCHEMA IF NOT EXISTS app; CREATE SCHEMA IF NOT EXISTS catalog;"
done
