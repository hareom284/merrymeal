# CLAUDE.md

Orientation for AI coding agents (and humans) working in this repo. README.md
is authoritative for setup and conventions — this file is a short index plus
the few extras agents need.

## What this is

MerryMeal — Django 5 + MySQL charity meal-delivery platform. Mobile-first
(Tailwind + Alpine + HTMX via CDN). Timezone `Australia/Melbourne`. Money is
stored as integer cents. Schema is locked — never invent new columns; check
the relevant sprint story first.

## Where to read first

- `README.md` — setup (Docker, macOS, Windows), commands, layout, conventions.
- `docs/product/sprints/sprint-XX/` — backlog, sprint plan, and per-story
  specs. Stories include exact file paths, code, and Definition of Done.
  Treat them as authoritative when implementing.
- `docs/superpowers/` — AI-oriented specs/plans (kept separate from the human
  developer tree in `docs/product/`).

## Core layout rules (recap from README)

- One package per concern: `models/`, `services/`, `forms/`, `views/`,
  `urls/`, `tests/`. One file per feature area (e.g. `auth.py`, `application.py`).
- **Models are schema-only** — fields, `Meta`, `__str__`, choice constants.
  No business methods. State changes live in `services/`.
- **Services own side effects** — DB writes that touch multiple tables, email
  dispatch, token issuance. Wrap multi-table writes in `transaction.atomic()`
  and defer email with `transaction.on_commit()`.
- **Cross-app dependencies**: `accounts`/`partners`/`dietary`/`meals`/
  `kitchens` are leaf apps; `dashboards` may import from any of them. Don't
  create reverse imports.
- **Views are thin**: `form.cleaned_data → service(...)` → redirect/render.

## Common commands

```bash
# Run tests
pytest

# Lint
ruff check .

# Apply lint auto-fixes
ruff check --fix .

# Env audit (CI gate — every env var read by code must appear in .env.example)
python scripts/check_env_example.py

# Seed lookups
python manage.py seed_cities
python manage.py seed_dietary
python manage.py seed_ingredients

# Run dev server
python manage.py runserver
```

## Things that bite

- **`.env.example` drift**: `scripts/check_env_example.py` is a CI gate. Any
  new `env(...)`, `os.getenv(...)` or `os.environ[...]` key must be added to
  `.env.example` with a `# comment` line above it, or CI fails.
- **Migrations**: column names, table names, and index names are locked by
  the story specs. If `makemigrations` produces a different name (e.g.
  auto-named index), edit the migration to use the spec name.
- **`auto_now=True` and `update_fields=`**: when you save with `update_fields`
  you must include `"updated_at"` in the list, or the timestamp won't fire.
- **Audit log actor**: admin write paths must call `set_actor(admin_user)`
  inside the transaction so `django-auditlog` records who did what.
- **Password tokens**: never store raw tokens. `issue_password_setup_token`
  returns a signed string for the URL; the DB row holds a SHA-256 hash. Use
  `select_for_update()` in the consume path — single-use.

## Working without AI tools (team convention)

Most of the team builds without AI. Anything you write — code, comments,
docs, story specs — must be self-sufficient for a human reader who has only
the file in front of them. No "AI generated" stubs, no TBDs, no half-finished
implementations. Tests live next to the feature; the story DoD is the bar.
