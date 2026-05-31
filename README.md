# MerryMeal

Charity meal-delivery platform — Django 5, mobile-first.

## Requirements

- **Python 3.12** (Homebrew: `brew install python@3.12`)
- **MySQL 8+** (Homebrew: `brew install mysql && brew services start mysql`)
- **Node 20+** (for Tailwind CSS build)
- macOS / Linux

No virtualenv. Deps install globally to Homebrew's Python 3.12.

> **Make `python3` mean Homebrew 3.12** — append this to `~/.zshrc`:
> ```
> export PATH="/opt/homebrew/opt/python@3.12/libexec/bin:$PATH"
> ```
> Then `source ~/.zshrc` (or open a new terminal). Otherwise `python3` resolves
> to Apple's bundled 3.9 which can't run Django 5 — use `python3.12` explicitly
> instead.

## Setup (one-time)

```bash
# Build deps for mysqlclient
brew install pkg-config

# Python deps
pip3 install --break-system-packages -r requirements.txt

# Tailwind
npm install
npm run build:css

# Database: create merrymeal DB + user
mysql -uroot <<SQL
CREATE DATABASE merrymeal CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
CREATE USER 'merrymeal'@'localhost' IDENTIFIED BY 'merrymeal';
GRANT ALL ON merrymeal.* TO 'merrymeal'@'localhost';
FLUSH PRIVILEGES;
SQL

# Env
cp .env.example .env

# Migrate + admin user
python3 manage.py migrate
python3 manage.py createsuperuser
```

> The `--break-system-packages` flag is needed because Homebrew Python 3.12
> declares itself "externally managed" (PEP 668). It's safe for a single-purpose
> dev machine; switch to a venv if you share Python with other projects.

## Run

```bash
python3 manage.py runserver
```

Open:
- App: <http://localhost:8000/accounts/login/>
- Admin: <http://localhost:8000/admin/>

## Tests

```bash
python3 -m pytest              # unit tests
ruff check .                      # lint
npm run watch:css                 # Tailwind watcher (dev)
```

## Layout

```
config/         Django settings (base/dev/prod/test) + root urls
apps/core/      Base models (timestamps, soft delete), Haversine, decorators
apps/accounts/  Custom User (email + role), login/logout, password reset
templates/      Mobile-first templates (HTMX + Alpine via CDN)
static/         Tailwind input + compiled output
```

## Planning docs (local-only, gitignored)

- Roadmap: `docs/superpowers/specs/2026-06-01-merrymeal-django-design.md`
- Phase 0 plan: `docs/superpowers/plans/2026-06-01-phase-0-foundation.md`
