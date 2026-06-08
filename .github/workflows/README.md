# CI workflows

| Job | Runs on | What it checks |
|---|---|---|
| lint | push + PR | `ruff check .` (and `.env.example` drift check, see Story 0.12). |
| test | push + PR | `pytest` against a MySQL 8 service container; uploads `coverage.xml`. |
| frontend | push + PR | `npm ci && npm run build:css`; fails if `static/dist` differs from committed CSS. |
| docker-smoke | PR only | Brings up `compose.yaml` and confirms the login page is reachable within 60 s. |
| playwright | PR only | Playwright at 375 × 667 px against the Docker stack. Required for merge. |
| release | push to main only | Builds the image and pushes `ghcr.io/hareom284/merrymeal:{latest,<sha>}`. Server pulls from there. |

All PR-gating jobs (lint/test/frontend/docker-smoke/playwright) are
required for merge to `main` (enforce in branch protection: Settings →
Branches → Add rule). The `release` job runs only AFTER a merge to main.
