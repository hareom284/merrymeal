# Sprint 01 — Finish foundation

**Weeks:** 1–2
**Primary epic:** [00 — Foundation](../../epics/00-foundation.md)
**Sprint goal:** every developer can `git clone && cp .env.example .env && docker compose up` and reach a working login screen in 60 seconds. CI is green on every PR. A Playwright test at 375 px protects the mobile-first promise.

---

## Stories pulled

| ID | Title | Track | Status | Detail |
|---|---|---|---|---|
| 0.9 | Docker-compose stack | Backend / Ops | planned (sprint-01) | [stories/0.9-docker-compose.md](stories/0.9-docker-compose.md) |
| 0.10 | GitHub Actions CI | Ops | planned (sprint-01) | [stories/0.10-github-actions-ci.md](stories/0.10-github-actions-ci.md) |
| 0.11 | Playwright mobile-viewport smoke test | Frontend | planned (sprint-01) | [stories/0.11-playwright-mobile-smoke.md](stories/0.11-playwright-mobile-smoke.md) |
| 0.12 | `.env.example` audit + onboarding checklist | Any | planned (sprint-01) | [stories/0.12-env-audit.md](stories/0.12-env-audit.md) |
| 0.13 | Production deploy skeleton | Ops (stretch) | planned (sprint-01) | [stories/0.13-prod-deploy-skeleton.md](stories/0.13-prod-deploy-skeleton.md) |

> **For executors:** each story file above is a self-contained TDD plan with file paths, code, commands, and expected output. Hand any story file to a developer (or an AI agent) — they need no other context to ship it.

**Sprint backlog & spillover protocol:** see [backlog.md](backlog.md).

Stories 0.1–0.8 are already `done (pre-backlog)` — see [Epic 00](../../epics/00-foundation.md).

---

## Parallel tracks

### Backend / Ops track — Dev A
1. **0.9 Docker-compose stack** — `compose.yaml`, `Dockerfile`, `docker-entrypoint.sh`, `.dockerignore`. Verify locally and on a teammate's laptop.
2. **0.10 GitHub Actions CI** — `.github/workflows/ci.yml` with lint, test, frontend jobs. Cache pip + node_modules.
3. **0.13 (stretch) Production deploy skeleton** — `compose.prod.yaml`, `deploy/nginx.conf.example`, `docs/deploy.md`. Only if 0.9 + 0.10 are merged by Wednesday of week 2.

### Frontend track — Dev B
1. **0.11 Playwright mobile-viewport smoke test** — `tests_e2e/playwright.config.ts`, `tests_e2e/login.spec.ts`, `npm run test:e2e`. Depends on 0.9 (CI runs the suite against the compose stack).
2. **0.12 `.env.example` audit** — read every `os.getenv` in `config/settings/*.py`, ensure each var is in `.env.example` with a comment. Update README "Setup" checklist.

If two devs: Dev A picks the backend lane, Dev B the frontend lane.
If three devs: Dev C focuses on 0.13 from day 1 plus helps unblock 0.10.

---

## Day-by-day suggestion

| Day | Backend / Ops | Frontend |
|---|---|---|
| Mon w1 | Sprint planning. Pull stories. Confirm DoR. | Sprint planning. Install Playwright. |
| Tue w1 | Draft `Dockerfile` + `compose.yaml`, get `web` + `mysql` healthy. | Draft `playwright.config.ts` + 1 dummy test against locally-running dev server. |
| Wed w1 | Add `redis` + `worker` containers. Validate end-to-end clone-to-login flow. | Begin `0.12` env audit. |
| Thu w1 | Open PR for 0.9. | Continue 0.12. Begin building real 0.11 test against the Docker stack. |
| Fri w1 | Mid-sprint review of 0.9 PR. Start `.github/workflows/ci.yml`. | Mid-sprint review. Tidy 0.11 PR draft. |
| Mon w2 | Land 0.9. CI scaffold begins. | Land 0.12 PR. Wire 0.11 to depend on the compose stack. |
| Tue w2 | Make pytest run against MySQL service container. | Continue. |
| Wed w2 | Mid-sprint demo: CI matrix passing. Begin 0.13 (stretch). | Land 0.11 PR. |
| Thu w2 | 0.13 deploy doc + `compose.prod.yaml`. | Help 0.13 (the deploy doc benefits from a frontend review). |
| Fri w2 | **Sprint demo + retro.** | Same. |

---

## Demo agenda (Fri w2)

1. Two laptops: a teammate's clean machine and the team lead's machine.
2. On the clean machine, `git clone … && cp .env.example .env && docker compose up`. Open login page within 60 seconds.
3. Show a green CI run on a deliberately-passing PR; show a red run on a deliberately-failing PR.
4. Show Playwright test result with screenshot at 375 × 667 px.
5. Walk through `docs/deploy.md` if 0.13 landed; otherwise note it as next-sprint carry-over.

## Definition of Done for the sprint

- All planned stories above have `STATUS: done (sprint-01)` in [Epic 00](../../epics/00-foundation.md).
- CI is enforced on `main` (no PR can merge red).
- README "Setup" section includes the Docker quickstart **and** the onboarding checklist.

## Risks for this sprint

| Risk | Mitigation |
|---|---|
| `mysqlclient` build inside the Docker image differs from host. | Pin both host (Homebrew MySQL major) and container (`mysql:8`) to the same major. |
| Playwright CI is flaky against the compose stack. | Add a 30 s readiness wait (`wait-for-it` on the `web` healthcheck) before the test suite runs. |
| 0.13 deploy doc grows out of scope. | Hard cap: skeleton only — no real VPS provisioning. Move provisioning to Sprint 11+. |
