# MerryMeal

Charity meal-delivery platform — Django 5, mobile-first.

## Requirements

- **Python 3.12**
- **MySQL 8+**
- **Node 20+** (for Tailwind CSS build)

No virtualenv. Deps install globally to Python 3.12.

---

## Setup — Docker (quickstart)

This path needs only Docker Desktop installed. No Python, MySQL, Node setup.

```bash
git clone <repo-url> merrymeal
cd merrymeal
cp .env.example .env
docker compose up
```

Open <http://localhost:8000/accounts/login/>. On first start, MySQL takes
~30 s to initialise; migrations then run automatically.

To create a superuser:

```bash
docker compose run --rm web python manage.py createsuperuser
```

To stop everything (and wipe the DB volume):

```bash
docker compose down -v
```

---

## Setup — macOS (Homebrew)

### 1. Install tools

```bash
brew install python@3.12 mysql pkg-config node
brew services start mysql
```

> **Make `python3` mean Homebrew 3.12** — append this to `~/.zshrc`:
> ```
> export PATH="/opt/homebrew/opt/python@3.12/libexec/bin:$PATH"
> ```
> Then `source ~/.zshrc` (or open a new terminal). Otherwise `python3`
> resolves to Apple's bundled 3.9 which can't run Django 5.

### 2. Python deps

```bash
pip3 install --break-system-packages -r requirements.txt
```

> `--break-system-packages` is needed because Homebrew Python 3.12
> declares itself "externally managed" (PEP 668). Safe for a
> single-purpose dev machine.

### 3. Database

```bash
mysql -uroot <<SQL
CREATE DATABASE merrymeal CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
CREATE USER 'merrymeal'@'localhost' IDENTIFIED BY 'merrymeal';
GRANT ALL ON merrymeal.* TO 'merrymeal'@'localhost';
FLUSH PRIVILEGES;
SQL
```

### 4. Env + migrate

```bash
cp .env.example .env
npm install
npm run build:css
python3 manage.py migrate
python3 manage.py createsuperuser
```

---

## Setup — Windows (PowerShell)

> Install all three from official installers — accept "Add to PATH" in
> each one. Then reopen PowerShell so the new PATH takes effect.

### 1. Install tools

- **Python 3.12** — <https://www.python.org/downloads/windows/>
  Check **"Add python.exe to PATH"** during install.
- **MySQL 8** — <https://dev.mysql.com/downloads/installer/>
  Use the MSI Installer; choose "Server only" or "Full". Set a **root
  password** when prompted and remember it.
- **Node 20+** — <https://nodejs.org/en/download>

Verify in a **new** PowerShell window:
```powershell
python --version       # Python 3.12.x
pip --version
node --version
mysql --version
```

If `mysql` is not on PATH, add `C:\Program Files\MySQL\MySQL Server 8.0\bin`
to your user PATH (System Properties → Environment Variables).

### 2. Python deps

```powershell
pip install -r requirements.txt
```

> No `--break-system-packages` flag needed on Windows. `mysqlclient`
> installs from a prebuilt wheel — no compiler required.

### 3. Database

Open a MySQL shell as root (it will prompt for the password you set
during install):

```powershell
mysql -uroot -p
```

Then at the `mysql>` prompt run:

```sql
CREATE DATABASE merrymeal CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
CREATE USER 'merrymeal'@'localhost' IDENTIFIED BY 'merrymeal';
GRANT ALL ON merrymeal.* TO 'merrymeal'@'localhost';
FLUSH PRIVILEGES;
EXIT;
```

### 4. Env + migrate

```powershell
Copy-Item .env.example .env
npm install
npm run build:css
python manage.py migrate
python manage.py createsuperuser
```

> On Windows the command is `python` (not `python3`). If `py` is what
> the launcher gave you, use `py -3.12` instead.

---

## Run

macOS / Linux:
```bash
python3 manage.py runserver
```

Windows:
```powershell
python manage.py runserver
```

Open:
- App: <http://localhost:8000/accounts/login/>
- Admin: <http://localhost:8000/admin/>

For production deploy, see [`docs/deploy.md`](docs/deploy.md).

---

## Seeded test users

`python3 manage.py seed_test_users` (also bundled into
`python3 manage.py seed_all`) creates one user per role with a shared
hard-coded password so any teammate can sign in and walk every
role-specific surface end-to-end. Re-running is safe — the seeder
upserts every user, the partner row, and the caregiver→member link.

| Email | Role | Password | Lands on |
|---|---|---|---|
| `member@test.merrymeal.local` | member | `testpass123` | `/dashboard/` |
| `caregiver@test.merrymeal.local` | caregiver | `testpass123` | `/dashboard/` (caregiver list, Story 3.8) |
| `volunteer@test.merrymeal.local` | volunteer | `testpass123` | `/volunteer/today/` |
| `donor@test.merrymeal.local` | donor | `testpass123` | `/donor/history/` |
| `kitchen_staff@test.merrymeal.local` | kitchen_staff | `testpass123` | `/kitchen/stock/receive/` |
| `partner@test.merrymeal.local` | partner-affiliated member | `testpass123` | `/partner/outcomes/` |

The platform super-admin is owned by a separate seeder, `seed_admin`,
and reads its email + password from `DJANGO_ADMIN_EMAIL` /
`DJANGO_ADMIN_PASSWORD`. If `DJANGO_ADMIN_PASSWORD` is empty, the
seeder generates a random password on first run and prints it once —
copy it from the terminal output.

---

## After setup — verify your environment

A teammate should be able to tick all of these after their first
`docker compose up` (or after the macOS / Windows native path):

- [ ] `http://localhost:8000/accounts/login/` returns the login screen.
- [ ] `http://localhost:8000/admin/` returns the Django admin login.
- [ ] `python3 -m pytest` (or `docker compose run --rm web pytest`) is green.
- [ ] `npm run watch:css` rebuilds Tailwind on file save.
- [ ] `python3 scripts/check_env_example.py` exits 0.
- [ ] (Optional) `npm run test:e2e` is green when the stack is up.

If any item fails, fix it **and** open a PR updating this checklist with
the missing step. The checklist is the contract.

---

## Tests

macOS / Linux:
```bash
python3 -m pytest        # unit tests (14 tests)
ruff check .             # lint
npm run watch:css        # Tailwind watcher (dev)
```

Windows:
```powershell
python -m pytest
ruff check .
npm run watch:css
```

---

## UI / Design system

**Stack:** Tailwind CSS 3 + HTMX + Alpine.js. No component library — every
class is plain Tailwind. Inter (body) + Playfair Display (headings) from
Google Fonts. Warm editorial palette tuned to match the prototype in
`01.html`.

**Custom design tokens** (`tailwind.config.js`):

| Token | Value | Use |
|---|---|---|
| `bg-warm-50` | `#faf9f8` | Page background |
| `bg-warm-100` | `#f5f4f1` | Card surface |
| `border-warm-200` | `#e8e6e1` | Borders |
| `text-warm-500` | `#827b6f` | Muted body text |
| `text-warm-800` / `text-warm-900` | `#2c2a28` / `#1a1917` | Body / headings |
| `bg-brand-green` | `#0f766e` (teal-700) | Primary CTAs, links, focus rings |
| `bg-brand-orange` | `#f97316` | Secondary accents |
| `font-display` | Playfair Display | Headings (h1–h3) |
| `font-sans` | Inter | Body |

**Reusable component classes** (`static/src/input.css`):

`.btn-primary`, `.btn-secondary`, `.input`, `.card`, `.label` — used in every
template so a future tweak (e.g. button radius) ripples through every screen.

**Interactive behavior** — for dropdowns, modals, tabs, and tooltips, use
**Alpine.js** (already loaded in `base.html`). Alpine is ~15 KB, lives inline
in HTML attributes (`x-data`, `x-show`, `@click`), and keeps us on plain
Tailwind without adopting a component library.

## Layout

```
config/                   Django settings (base/dev/prod/test) + root urls
apps/
├── core/                 Shared infrastructure
│   ├── models/           Abstract bases (fields only)
│   │   ├── timestamped.py
│   │   └── soft_delete.py
│   ├── services/         Generic operations
│   │   └── soft_delete.py   soft_delete(instance)
│   ├── managers.py       Query layer (e.g. soft-delete filter)
│   ├── geo.py            Haversine helper (10 km rule)
│   └── decorators.py     @role_required
├── accounts/             Identity + applications + addresses + caregivers + cities
│   ├── models/           Data — schema only (fields, Meta, choices)
│   │   ├── users.py      User (zero methods other than __str__)
│   │   ├── cities.py     City (lookup for address suburb dropdown)
│   │   ├── addresses.py  Address (lat/lng + FK to City)
│   │   ├── caregiver_links.py  CaregiverLink (member ↔ caregiver relationship)
│   │   ├── applications.py     Application (3-step intake wizard rows)
│   │   └── password_setup_tokens.py  Single-use welcome-link tokens
│   ├── managers/         Query-layer plumbing (Django contract)
│   │   └── users.py      UserManager (create_user etc — Django-required)
│   ├── services/         Business logic — state changes & side effects
│   │   ├── auth.py       sign_in(), sign_out()
│   │   ├── users.py      create_user(), delete_user()
│   │   ├── caregiver_links.py     link_caregiver()
│   │   ├── application.py         create_draft_application(), update_application_address(), submit_application()
│   │   └── password_setup_tokens.py  issue/consume welcome tokens
│   ├── forms/            HTML rendering + validation
│   │   ├── auth.py       EmailLoginForm
│   │   └── application.py  ApplicationContact/Address/DietaryForm (3 wizard steps)
│   ├── views/            HTTP layer — thin: form.cleaned_data → service
│   │   ├── auth.py       login_view, logout_view
│   │   └── application.py  application_step_1/2/3, application_done
│   ├── urls/             Routing
│   │   ├── auth.py       /login/, /logout/
│   │   ├── application.py  /apply/, /apply/address/, /apply/dietary/, /apply/done/
│   │   └── password_reset.py
│   ├── backends.py       EmailBackend
│   └── admin.py
├── partners/             Partner orgs (charities, restaurants, suppliers, corporates)
│   ├── models/           Partner — schema only
│   ├── admin.py
│   └── tests/
├── dietary/              Diet preferences + allergies + user join tables
│   ├── models/           DietPreference, Allergy, UserDietPreference, UserAllergy
│   ├── management/       seed_dietary command (8 prefs + 7 allergies, idempotent)
│   ├── admin.py
│   └── tests/
├── dashboards/           Landing page + member dashboard + admin approval queue
│   ├── views/            landing, member, admin_applications_list/detail/approve/reject
│   ├── services/         approve_application(), reject_application()
│   ├── urls/             /, /dashboard/, /admin/applications/...
│   └── tests/
├── meals/                Meal catalogue
│   ├── models/           Meal (soft-delete enabled)
│   ├── admin.py
│   └── tests/
└── kitchens/             Kitchens + ingredients + stock batches + meal recipes
    ├── models/           Kitchen, Ingredient, MealIngredient, IngredientBatch
    ├── services/         receive_batch() — atomic stock receipt
    ├── forms/            StockReceiveForm
    ├── views/            stock_receive_view (kitchen_staff/admin only)
    ├── urls/             /kitchen/stock/receive/
    ├── management/       seed_ingredients (30 staples, idempotent)
    ├── admin.py          + ExpiringSoonFilter
    └── tests/
templates/                Mobile-first templates (HTMX + Alpine via CDN)
static/                   Tailwind input + compiled output
```

**Layering convention.** Every app uses **packages** (not single files) for
`models/`, `managers/`, `services/`, `forms/`, `views/`, `urls/`. One file
per feature area (`auth.py`, later `profile.py`, `referral.py`, …).
`__init__.py` re-exports public names so external code stays unchanged:
`from apps.accounts.models import User`, `include("apps.accounts.urls")`.

> **No `requests/` layer for HTML flows.** Django Forms already do what
> Laravel `FormRequest` does — format validation + a `.cleaned_data` dict.
> Adding a separate request DTO just to repackage it is ceremony without
> safety. When a second input source appears (HTMX JSON endpoint, mobile
> API), introduce `requests/` then — at that point it pays for itself by
> giving services one input contract across HTML, JSON, and CLI.

**Models are schema-only.** A model file contains fields, `Meta` (table name,
indexes), `__str__`, and choice constants — that's it. No `delete()` overrides,
no `apply_for_membership()` methods, no `send_welcome_email()`. Anything that
mutates state, has side effects, or coordinates other models lives in
`services/`. Querying patterns (e.g. soft-delete filters) live on managers,
not on model methods.

> **Why the strict rule:** Django happily lets you put logic on models,
> but it creates two problems: (1) it's invisible from the call site —
> `user.delete()` looks like a hard delete but secretly soft-deletes; (2) it
> ties business rules to ORM lifecycle in ways that hurt testability. A
> service function with named parameters makes the intent obvious.

**Framework exceptions.** Two methods on `UserManager` (`create_user`,
`create_superuser`) stay because Django's `createsuperuser` command and the
`AbstractBaseUser` contract require them. They are framework plumbing,
not app logic. App code should call `apps.accounts.services.create_user`
instead — it wraps the manager and is the recommended entry point.

**Request flow** (login example):

```
POST /accounts/login/
        │
        ▼
views/auth.py        HTTP layer — parse, route, render
        │  binds → EmailLoginForm        (forms/auth.py — fields + validation)
        │  splats form.cleaned_data
        ▼
services/auth.py     Business logic — sign_in(request, *, email, password)
        │  authenticate + login()
        ▼
models/users.py      Data — User row
```

Why: forms know about HTML widgets and validation, services know about side
effects. Each layer is testable in isolation (services accept plain kwargs;
forms can be unit-tested with `EmailLoginForm({"email": "...", ...})`).

---

## Troubleshooting

| Symptom | Cause | Fix |
|---|---|---|
| `ModuleNotFoundError: No module named 'environ'` (macOS) | `python3` is Apple's 3.9, not Homebrew 3.12 | Add the PATH line to `~/.zshrc` (see step 1) or call `python3.12` explicitly |
| `mysqlclient` build fails on macOS | `pkg-config` or MySQL headers missing | `brew install pkg-config mysql` |
| `'python' is not recognized` (Windows) | Python not on PATH | Re-run the Python installer and tick "Add to PATH", or use `py -3.12` |
| `Access denied for user 'root'` (Windows) | MySQL root has a password | Use `mysql -uroot -p` and enter the password you set at install |
| Admin login: "Please enter the correct email and password for a staff account" | User doesn't exist or wrong password | `python manage.py createsuperuser` (or `changepassword <email>`) |

---

## Planning docs (local-only, gitignored)

- Roadmap: `docs/superpowers/specs/2026-06-01-merrymeal-django-design.md`
- Phase 0 plan: `docs/superpowers/plans/2026-06-01-phase-0-foundation.md`
