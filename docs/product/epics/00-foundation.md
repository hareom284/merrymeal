# Epic 00 — Foundation

> **Goal:** an empty but production-shaped Django app a developer can clone,
> run, and deploy. Nothing user-visible beyond a login screen.

**Sprints:** 1 (Sprint 01)
**Status:** **partially done** — most code-level scaffolding exists. CI, Docker, and Playwright are outstanding.
**Source spec:** [Roadmap §6, Phase 0](../../superpowers/specs/2026-06-01-merrymeal-django-design.md)

---

## Why this epic exists

Every following epic assumes:

1. A Django project boots, runs migrations, serves a page.
2. A developer can clone the repo, follow `README.md`, and have a working local
   stack in ≤ 30 minutes — on macOS **and** Windows.
3. CI catches lint + test failures before they hit `main`.
4. The mobile-first promise is enforceable, not aspirational — there is a
   browser-level test running at 375 px viewport in CI.

If any one of those is false, the team will pay tax on every later sprint.

---

## Stories

> Stories already shipped before this backlog was written are listed for
> context with `STATUS: done (pre-backlog)`. Skip them when planning.

### Story 0.1 — Django 5 project with split settings
**STATUS: done (pre-backlog)**

**As a** developer
**I want** the Django project to load the correct settings per environment
**so that** local dev, CI, and prod can never share a misconfigured DB or secret.

**Acceptance criteria:**
- [x] `config/settings/base.py` holds shared config.
- [x] `config/settings/dev.py`, `prod.py`, `test.py` extend `base.py`.
- [x] `DJANGO_SETTINGS_MODULE` selectable per environment.
- [x] `manage.py runserver` works on macOS and Windows.

**Files (reference):** `config/settings/{base,dev,prod,test}.py`, `manage.py`, `config/urls.py`.

---

### Story 0.2 — `core` app with abstract base models
**STATUS: done (pre-backlog)**

**As a** backend developer
**I want** `TimeStampedModel` and `SoftDeleteModel` available in `apps/core`
**so that** every app inherits the same `created_at` / `updated_at` / `deleted_at` contract that the SQL schema expects.

**Acceptance criteria:**
- [x] `apps/core/models/timestamped.py` defines `TimeStampedModel` (abstract).
- [x] `apps/core/models/soft_delete.py` defines `SoftDeleteModel` (abstract).
- [x] `apps/core/managers.py` provides a manager that filters out
      `deleted_at IS NOT NULL` by default and exposes `all_objects` for the
      unfiltered queryset.
- [x] `apps/core/services/soft_delete.py::soft_delete(instance)` is the only
      public entry point that sets `deleted_at`. Models do not override `.delete()`.

**Files (reference):** `apps/core/models/`, `apps/core/managers.py`, `apps/core/services/soft_delete.py`.

---

### Story 0.3 — Haversine helper (10 km rule foundation)
**STATUS: done (pre-backlog)**

**As a** backend developer
**I want** a single, tested Haversine function in `core/geo.py`
**so that** every later feature that asks "is this member within X km of that kitchen?" uses the same math.

**Acceptance criteria:**
- [x] `apps/core/geo.py::haversine_km(lat1, lng1, lat2, lng2) -> float`.
- [x] Unit tests cover: (a) zero distance, (b) ~10 km known pair, (c)
      antipodal points (~20 015 km).
- [x] Returns kilometres as `float`, rounded to two decimal places.

**Files (reference):** `apps/core/geo.py`, `apps/core/tests/test_geo.py`.

---

### Story 0.4 — `@role_required` decorator
**STATUS: done (pre-backlog)**

**As a** backend developer
**I want** a single decorator that gates a view to one or more roles
**so that** every later view uses the same authorization check rather than ad-hoc `if request.user.role == ...` scattered around.

**Acceptance criteria:**
- [x] `apps/core/decorators.py::role_required(*roles)` returns a decorator.
- [x] Unauthenticated users → redirect to login.
- [x] Authenticated but wrong role → HTTP 403.
- [x] Right role → view runs normally.
- [x] Unit tests cover all three paths.

---

### Story 0.5 — Custom `User` model
**STATUS: done (pre-backlog)**

**As a** Django developer
**I want** a custom `User` model matching the schema
**so that** the `users` table has the columns the rest of the system expects: `role`, `dob`, `partner_id`, and soft delete via `deleted_at`.

**Acceptance criteria:**
- [x] `apps/accounts/models/users.py::User` extends `AbstractBaseUser` + `PermissionsMixin`.
- [x] Email is the username field (unique, indexed).
- [x] `role` choices match the schema: `member`, `volunteer`, `caregiver`,
      `donor`, `kitchen_staff`, `admin`.
- [x] `dob` is `DateField(null=True, blank=True)`.
- [x] `partner_id` is FK to `partners.Partner` (nullable). Note: introduced
      formally in Epic 01 when `partners` app exists; for Epic 00 the field
      may be commented out and added back with a migration in Story 1.5.
- [x] Soft delete via `deleted_at` and the `core` manager.

---

### Story 0.6 — Email login + logout + password reset
**STATUS: done (pre-backlog)**

**As a** member, caregiver, volunteer, donor, kitchen staff, or admin
**I want** to log in with my email and password and reset it if I forget
**so that** I can access the screens for my role.

**Acceptance criteria:**
- [x] `apps/accounts/forms/auth.py::EmailLoginForm`.
- [x] `apps/accounts/views/auth.py::login_view`, `logout_view`.
- [x] `apps/accounts/backends.py::EmailBackend` configured in `AUTHENTICATION_BACKENDS`.
- [x] URLs: `/accounts/login/`, `/accounts/logout/`.
- [x] Password-reset flow wired: `/accounts/password_reset/` → email → confirm.
- [x] Mobile-first login template at 375 px.

---

### Story 0.7 — Tailwind + HTMX + Alpine wiring
**STATUS: done (pre-backlog)**

**As a** frontend developer
**I want** Tailwind compiled, HTMX and Alpine loaded in `base.html`
**so that** every later screen can be built with the same tokens and progressive-enhancement pattern.

**Acceptance criteria:**
- [x] `npm run build:css` and `npm run watch:css` work.
- [x] `tailwind.config.js` defines warm-palette + brand-green/orange tokens
      documented in `README.md`.
- [x] `static/src/input.css` exports `.btn-primary`, `.btn-secondary`, `.input`,
      `.card`, `.label` component classes.
- [x] `templates/base.html` loads HTMX and Alpine via CDN.

---

### Story 0.8 — pytest + factory-boy scaffolding
**STATUS: done (pre-backlog)**

**As a** developer
**I want** to run `pytest` from the repo root and see a clean result
**so that** TDD is the default workflow.

**Acceptance criteria:**
- [x] `pytest.ini` configured for Django settings = `config.settings.test`.
- [x] `pyproject.toml` declares dev deps.
- [x] At least 14 baseline tests pass (geo, decorators, auth, soft-delete).
- [x] `ruff check .` passes.

---

### Story 0.9 — Docker-compose stack
**STATUS: backlog**

**As a** developer joining the project
**I want** `docker compose up` to give me `web`, `mysql`, `redis`, and a `worker` container
**so that** I do not have to install MySQL or Redis on my host machine and CI uses the same images.

**User story:**
> As a developer
> I want a one-command local stack
> so that onboarding takes 5 minutes instead of an afternoon, and my laptop
> matches CI matches prod.

**Acceptance criteria:**
- [ ] `compose.yaml` at repo root with services: `web`, `mysql`, `redis`, `worker`.
- [ ] `web` reads `.env` and waits for `mysql` (use `depends_on` + healthcheck).
- [ ] `mysql` uses MySQL 8 image, persists data to a named volume, env vars
      match `.env.example`.
- [ ] `redis` uses Redis 7-alpine.
- [ ] `worker` runs `python manage.py qcluster` (Django-Q2).
- [ ] `docker compose up` from a fresh clone (after `cp .env.example .env`)
      reaches a working `http://localhost:8000/accounts/login/` in ≤ 60 s.
- [ ] `README.md` "Setup" section gains a **third path**: "Setup — Docker"
      with a 5-line quickstart.

**Technical notes:**
- New files: `compose.yaml`, `Dockerfile` (multi-stage: `node` builder for
  Tailwind → `python:3.12-slim` runner), `.dockerignore`.
- `docker-entrypoint.sh` runs `migrate` then `gunicorn` (prod) or
  `runserver` (dev).
- `worker` service shares the same image but overrides `command`.
- Healthcheck: `mysqladmin ping` for MySQL, `redis-cli ping` for Redis.

**DB tables touched:** none (infrastructure only).

**Mobile viewport:** N/A.

**Test strategy:**
- Manual: `docker compose up` from a fresh clone on a teammate's laptop;
  login page reachable.
- CI: smoke job runs `docker compose up -d` and curls the login URL.

**Definition of done:** see `README.md` Definition of Done.

---

### Story 0.10 — GitHub Actions CI (ruff + pytest + Tailwind build)
**STATUS: backlog**

**User story:**
> As a developer reviewing a PR
> I want CI to tell me the PR is safe to merge
> so that I do not need to run every check by hand.

**Acceptance criteria:**
- [ ] `.github/workflows/ci.yml` runs on every push and PR.
- [ ] Jobs (run in parallel where independent):
  - `lint` — `ruff check .` on Python 3.12.
  - `test` — `pytest` against a MySQL 8 service container; reports coverage.
  - `frontend` — `npm ci && npm run build:css`; fails if output diff.
- [ ] CI uses the same MySQL major version as prod.
- [ ] CI uploads test artefacts (coverage report) for the last run.
- [ ] PR cannot be merged with a failing required check.

**Technical notes:**
- New files: `.github/workflows/ci.yml`.
- Use the `mysql:8` GitHub Actions service container with the same env vars
  as `compose.yaml`.
- Cache `~/.cache/pip` and `node_modules` keyed on lock-file hashes.

**Mobile viewport:** N/A.

**Test strategy:** validate by opening a deliberately-failing PR and watching the matrix go red.

---

### Story 0.11 — Playwright mobile-viewport smoke test
**STATUS: backlog**

**User story:**
> As the team
> I want one Playwright test that opens the login screen at 375 × 667 px
> so that the mobile-first promise is enforced by CI on every PR.

**Acceptance criteria:**
- [ ] `tests_e2e/` contains a `playwright.config.ts` set to viewport `{ width: 375, height: 667 }`.
- [ ] `tests_e2e/login.spec.ts` opens `/accounts/login/`, asserts the email
      field is visible and tappable (≥ 44 px tall), and that no horizontal
      scrollbar appears at 375 px.
- [ ] `npm run test:e2e` runs the suite.
- [ ] CI runs the suite headless against the Docker stack from Story 0.9
      (CI job depends on Story 0.9 being done).

**Technical notes:**
- New files: `tests_e2e/playwright.config.ts`, `tests_e2e/login.spec.ts`,
  `package.json` script `test:e2e`.
- `tests_e2e/` already exists (empty) — populate it.

**Mobile viewport:** the whole point.

**Test strategy:** the test itself.

---

### Story 0.12 — `.env.example` audit + onboarding checklist
**STATUS: backlog**

**User story:**
> As a developer cloning the repo for the first time
> I want `.env.example` to list every variable I need
> so that I do not waste an hour discovering missing config.

**Acceptance criteria:**
- [ ] Every setting read by `config/settings/*.py` is represented in `.env.example`.
- [ ] Each variable has an inline comment explaining its purpose.
- [ ] Secrets in `.env.example` are placeholder values (`change-me`,
      `replace-with-real-key`), never real credentials.
- [ ] `README.md` "Setup" section ends with a **checklist** of what should
      work after setup: login page reachable, admin reachable, `pytest`
      green, Tailwind watcher running.

**Technical notes:** purely docs + `.env.example`.

**Mobile viewport:** N/A.

**Test strategy:** a teammate follows the README on a fresh laptop and
ticks the checklist. If any step fails, the README is broken — fix it.

---

### Story 0.13 — Production deploy skeleton (Nginx + Gunicorn)
**STATUS: backlog (deferred to end of Sprint 01 if time allows)**

**User story:**
> As an operations engineer
> I want a documented, repeatable production deploy recipe
> so that the first production push is a 30-minute task, not an investigation.

**Acceptance criteria:**
- [ ] `deploy/nginx.conf.example` with HTTPS, HSTS, gzip, static-file caching.
- [ ] `deploy/gunicorn.service.example` (systemd unit).
- [ ] `docs/deploy.md` walks through: provision VPS → install Docker → clone
      → `.env` → `docker compose -f compose.yaml -f compose.prod.yaml up -d`.
- [ ] Compose override file `compose.prod.yaml` sets `DEBUG=False`,
      `ALLOWED_HOSTS`, secure cookie flags.

**Technical notes:** no app code; pure ops scaffolding.

**Mobile viewport:** N/A.

**Test strategy:** dry-run on a Hetzner CX11 or equivalent disposable VPS.

---

## Backlog (not in any sprint yet)

After Sprint 01 closes, anything still `backlog` here moves to Epic 07 for later opportunistic pickup.

---

## Demo for end of Epic 00

A teammate clones the repo on a new laptop, runs:

```
cp .env.example .env
docker compose up
```

…and within 60 seconds opens `http://localhost:8000/accounts/login/` on a
phone-sized browser window, logs in as the superuser, and sees the (empty)
dashboard. CI on the same PR is green.
