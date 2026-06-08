#!/usr/bin/env bash
# Story 0.9 acceptance test:
# `docker compose up` from a fresh clone reaches the login page in ≤ 60 s.
set -euo pipefail

cleanup() {
  docker compose down -v >/dev/null 2>&1 || true
}
trap cleanup EXIT

# 1. Bring up the stack detached.
docker compose up -d --build

# 2. Poll the login URL for up to 60 s.
deadline=$(( $(date +%s) + 60 ))
while [ "$(date +%s)" -lt "$deadline" ]; do
  if curl -fs "http://localhost:8000/accounts/login/" >/dev/null; then
    echo "OK: login page reachable"
    exit 0
  fi
  sleep 2
done

echo "FAIL: login page not reachable within 60 s"
docker compose logs --no-color web
exit 1
