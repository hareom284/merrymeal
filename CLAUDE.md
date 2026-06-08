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
- `docs/superpowers/handoffs/` — per-sprint resume notes. Read the latest one
  before starting work; it lists what's done, what's blocked, and the
  spec-vs-codebase substitutions to apply.

## Sprint status (snapshot — update after each sprint lands)

| Sprint | Epic | Status | Notes |
|---|---|---|---|
| 01–06 | 00–03 | done | foundations, accounts, kitchens, planning |
| 07 | 04 | done | volunteer Availability + delivery models + dispatch |
| 08 | 04 | done | volunteer today screen, mark-delivered, feedback, caregiver alert |
| 09 | 05 | done | donations + Stripe checkout |
| 10 | 06 | done | admin home, partner outcomes, donor history, FY receipt, board report, audit viewer, partner referral form |
| 11 | 07 | not started | hardening (PWA, encryption, WCAG, perf budget) |

Branch convention: each sprint's work merges into `implement-sprint-02`
(the long-running integration branch) via per-story commits tagged `[X.Y]`.

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
# Run tests (use the test settings — SQLite + sync Q_CLUSTER; MUCH faster than dev)
DJANGO_SETTINGS_MODULE=config.settings.test python3 -m pytest -q

# Single story's tests
DJANGO_SETTINGS_MODULE=config.settings.test python3 -m pytest apps/<app>/tests/test_<feature>.py -v

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

# Run dev server (MySQL via Docker compose; see README)
python manage.py runserver

# Playwright (TypeScript, mobile-chrome project = iPhone SE / WebKit)
cd tests_e2e && BASE_URL=http://localhost:8000 npx playwright test <spec>.spec.ts --project=mobile-chrome
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
- **Time pinning in tests**: `freezegun` / `pytest-freezer` are NOT installed.
  Use the in-house `freezer` fixture pattern (monkeypatches
  `django.utils.timezone.localdate`) — copied into `apps/delivery/tests/conftest.py`
  for sprint 7+, original at `apps/planning/tests/test_validate_command.py`.
- **DJ012 lint**: model magic methods (`__str__`, `clean`) must appear before
  any custom methods inside the class body. Common ruff failure on first save.

## Spec-vs-codebase substitution catalog

Story specs were written against a slightly different model layout than what
exists. When you see these in a spec, swap to the real name:

| Spec says | Real name |
|---|---|
| `apps.deliveries` (plural) | `apps.delivery` (singular) |
| `accounts.UserAddress` model / FK string | `accounts.Address` (db_table `user_addresses`) |
| `MemberFactory` | `UserFactory(role="member")` |
| `apps.planning.tests.factories.KitchenFactory` | `apps.kitchens.tests.factories.KitchenFactory` |
| `Kitchen.is_active` filter | the field doesn't exist; use `Kitchen.objects.all()` and note the discrepancy |
| `freezegun.freeze_time` decorator | the `freezer` fixture + `freezer.move_to("YYYY-MM-DD")` |
| `User.role == "partner"` gate | `User.partner_id is not None` (no `partner` role in `ROLE_CHOICES`) |
| `assign_meal_type(..., scheduled_date=)` | the kwarg is `service_date=` |

## Sprint execution playbook

1. `docs/superpowers/handoffs/sprint-<N>-resume.md` — read it FIRST if it
   exists. Lists what's done, blocked, and any in-flight branches.
2. For each story `docs/product/sprints/sprint-<N>/stories/<X.Y>-*.md`:
   spec is authoritative. Follow TDD: write the failing test, implement,
   run targeted tests, full sweep, ruff fix, commit.
3. Commit per-story with message `<type>(<app>): <summary> [<X.Y>]`.
   The trailing `[X.Y]` tag is searchable in `git log --oneline`.
4. After all stories: update `STATUS: done (sprint-<N>)` in the relevant
   epic file under `docs/product/epics/`.

### Running stories in parallel (multi-agent dispatch)

When the user asks for parallel implementation, use a git worktree:

```bash
# Create an isolated worktree based off main
# (the EnterWorktree tool handles this; manual fallback below)
git worktree add .claude/worktrees/sprint-<N> -b worktree-sprint-<N> origin/main
cd .claude/worktrees/sprint-<N>
```

Inside the worktree, dispatch one subagent per *independent* story. The
shared-state risk is small but real:

- `config/urls.py` — read it before editing; append your include, preserve
  others.
- `config/settings/base.py::INSTALLED_APPS` — append; never reorder.
- `apps/dashboards/urls/admin.py` — multiple stories add admin routes here;
  read before editing.

Don't dispatch agents that depend on each other in parallel — finish one,
commit, then dispatch the next round.

## Working without AI tools (team convention)

Most of the team builds without AI. Anything you write — code, comments,
docs, story specs — must be self-sufficient for a human reader who has only
the file in front of them. No "AI generated" stubs, no TBDs, no half-finished
implementations. Tests live next to the feature; the story DoD is the bar.
