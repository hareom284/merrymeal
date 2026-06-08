# CI workflows

| Job | Runs on | What it checks |
|---|---|---|
| lint | push + PR | `ruff check .` (and `.env.example` drift check, see Story 0.12). |
| test | push + PR | `pytest` against a MySQL 8 service container; uploads `coverage.xml`. |
| frontend | push + PR | `npm ci && npm run build:css`; fails if `static/dist` differs from committed CSS. |
| docker-smoke | PR only | Brings up `docker-compose.yml` and confirms the login page is reachable within 60 s. |
| release | push to main only | Builds the image and pushes `ghcr.io/hareom284/merrymeal:{latest,<sha>}`. Server pulls from there. |
| deploy | push to main only | SSHes into the production server, runs `docker compose pull && up -d`. Requires the secrets listed below. |

All PR-gating jobs (lint/test/frontend/docker-smoke) are required for
merge to `main` (enforce in branch protection: Settings → Branches →
Add rule). The `release` + `deploy` jobs run only AFTER a merge to main.

## Required secrets for the `deploy` job

Set these under Settings → Secrets and variables → Actions → New repository secret:

| Secret | Value | Notes |
|---|---|---|
| `DEPLOY_HOST` | Server IP or hostname | e.g. `203.0.113.42` or `merrymeal.freebarcodeqr.com` |
| `DEPLOY_USER` | SSH user | `root`, or a sudoer with **passwordless** sudo configured |
| `DEPLOY_SSH_KEY` | Private SSH key (full PEM) | Generate a deploy-only key: `ssh-keygen -t ed25519 -f deploy_key -N ""`. Add `deploy_key.pub` to `~/.ssh/authorized_keys` on the server, paste `deploy_key` contents here. |
| `DEPLOY_PORT` | _(optional)_ SSH port | Defaults to `22` if unset. |

The `deploy` job runs only after `release` succeeds, so the new image is
guaranteed to be on GHCR before the server tries to pull it.
