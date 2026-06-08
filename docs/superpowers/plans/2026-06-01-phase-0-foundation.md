# Phase 0 — Foundation Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Stand up an empty but production-shaped Django 5 project for MerryMeal with custom user model, Docker, mobile-first base template, and CI — ready for Phase 1 feature work.

**Architecture:** Single Django project with `apps/` namespace. Split settings (`base`/`dev`/`prod`/`test`). Custom `User` extends `AbstractUser`. Tailwind CSS compiled by Node CLI. HTMX + Alpine.js as classic `<script>` tags. MySQL 8 in dev and prod (Homebrew-managed locally). pytest uses SQLite in-memory for speed.

**Tech Stack:** Python 3.12 (Homebrew, no venv), Django 5.x, MySQL 8 (Homebrew brew services), `mysqlclient`, Tailwind CSS 3, HTMX 1.9, Alpine.js 3, pytest-django, factory-boy, Playwright, ruff.

**Python install convention:** Homebrew `python@3.12` invoked as `python3.12` / `pip3.12`. Deps installed globally with `pip3.12 install --break-system-packages -r requirements.txt` (PEP 668 override). No virtualenv.

---

## File Structure (created/touched in this plan)

```
merrymeal/
├── manage.py                          # Django entry point
├── requirements.txt                   # Python deps (pip3.12 install -r)
├── pyproject.toml                     # ruff config only
├── README.md                          # no-venv quickstart
├── package.json                       # Tailwind build
├── tailwind.config.js                 # Tailwind config (mobile-first)
├── pytest.ini                         # pytest-django config
├── playwright.config.py               # mobile viewport defaults
├── .env.example                       # documented env vars
├── .gitignore                         # add Python + Node + Django paths
├── README.md                          # quickstart
├── config/
│   ├── __init__.py
│   ├── settings/
│   │   ├── __init__.py
│   │   ├── base.py                    # shared settings
│   │   ├── dev.py                     # DEBUG=True, local DB
│   │   ├── prod.py                    # DEBUG=False, env-driven
│   │   └── test.py                    # SQLite, faster hashers
│   ├── urls.py
│   ├── wsgi.py
│   └── asgi.py
├── apps/
│   ├── __init__.py
│   ├── core/
│   │   ├── __init__.py
│   │   ├── apps.py
│   │   ├── models/                    # schema only (fields, Meta)
│   │   │   ├── __init__.py
│   │   │   ├── timestamped.py         # TimeStampedModel
│   │   │   └── soft_delete.py         # SoftDeleteModel (no behavior)
│   │   ├── services/                  # generic operations
│   │   │   ├── __init__.py
│   │   │   └── soft_delete.py         # soft_delete(instance) helper
│   │   ├── managers.py                # SoftDeleteManager, AllObjectsManager
│   │   ├── geo.py                     # haversine_km()
│   │   ├── decorators.py              # role_required()
│   │   └── tests/
│   │       ├── __init__.py
│   │       ├── test_models.py
│   │       ├── test_geo.py
│   │       └── test_decorators.py
│   └── accounts/
│       ├── __init__.py
│       ├── apps.py
│       ├── models/                    # schema only (fields, Meta)
│       │   ├── __init__.py
│       │   └── users.py               # User — no methods except __str__
│       ├── managers/                  # Django-required query plumbing
│       │   ├── __init__.py
│       │   └── users.py               # UserManager (create_user, etc.)
│       ├── services/                  # business logic + side effects
│       │   ├── __init__.py
│       │   ├── auth.py                # sign_in(), sign_out()
│       │   └── users.py               # create_user(), delete_user()
│       ├── forms/                     # HTML widgets + format validation
│       │   ├── __init__.py
│       │   └── auth.py                # EmailLoginForm
│       ├── views/                     # thin HTTP layer
│       │   ├── __init__.py
│       │   └── auth.py                # login_view, logout_view
│       ├── urls/                      # routing
│       │   ├── __init__.py            # app_name + composed urlpatterns
│       │   ├── auth.py                # /login/, /logout/
│       │   └── password_reset.py      # /password_reset/*, /reset/*
│       ├── backends.py                # EmailBackend
│       ├── admin.py
│       ├── migrations/
│       │   └── 0001_initial.py
│       └── tests/
│           ├── __init__.py
│           ├── factories.py           # UserFactory
│           ├── test_models.py
│           ├── test_services.py
│           ├── test_views.py
│           └── test_password_reset.py
├── templates/
│   ├── base.html                      # mobile-first shell
│   ├── partials/
│   │   └── _nav.html
│   └── accounts/
│       └── login.html
├── static/
│   └── src/
│       └── input.css                  # Tailwind directives
├── tests_e2e/
│   ├── __init__.py
│   ├── conftest.py
│   └── test_smoke_login.py            # Playwright mobile viewport
└── .github/workflows/
    └── ci.yaml                        # ruff + pytest + playwright
```

---

## Task 1: Bootstrap repo with `requirements.txt`, `pyproject.toml`, `.env.example`

**Files:**
- Create: `requirements.txt`
- Create: `pyproject.toml` (ruff config only)
- Create: `.gitignore`
- Create: `.env.example`

- [ ] **Step 1: Write `requirements.txt`**

```text
# Runtime
django>=5.0,<5.2
mysqlclient>=2.2,<3
django-environ>=0.11,<1
django-q2>=1.7,<2
redis>=5,<6
django-storages[s3]>=1.14,<2
django-auditlog>=3,<4
gunicorn>=23,<24
whitenoise>=6,<7

# Dev / test
pytest>=8,<9
pytest-django>=4.8,<5
factory-boy>=3.3,<4
playwright>=1.45,<2
ruff>=0.6,<1
ipython>=8,<9
```

- [ ] **Step 1b: Write `pyproject.toml` (ruff only — no deps, no setuptools build)**

```toml
[tool.ruff]
line-length = 100
target-version = "py312"

[tool.ruff.lint]
select = ["E", "F", "W", "I", "B", "UP", "DJ"]
ignore = ["E501"]
```

- [ ] **Step 2: Write `.gitignore`**

```gitignore
# Python
__pycache__/
*.py[cod]
*$py.class
*.egg-info/
.venv/
.python-version

# Django
*.sqlite3
media/
staticfiles/
*.log

# Tailwind / Node
node_modules/
static/dist/

# Env
.env
.env.local

# IDE
.vscode/
.idea/
.DS_Store

# Tests
.pytest_cache/
.coverage
htmlcov/
playwright-report/
test-results/
```

- [ ] **Step 3: Write `.env.example`**

```dotenv
# Django
DJANGO_SETTINGS_MODULE=config.settings.dev
DJANGO_SECRET_KEY=change-me-in-prod
DJANGO_DEBUG=True
DJANGO_ALLOWED_HOSTS=localhost,127.0.0.1

# Database
DATABASE_URL=mysql://merrymeal:merrymeal@127.0.0.1:3306/merrymeal

# Redis (Phase 0 doesn't require it; needed in later phases)
REDIS_URL=redis://localhost:6379/0
```

- [ ] **Step 4: Commit**

```bash
git add requirements.txt pyproject.toml .gitignore .env.example
git commit -m "chore: scaffold Python project metadata and env template"
```

---

## Task 2: Bootstrap Django project skeleton

**Files:**
- Create: `manage.py`
- Create: `config/__init__.py`, `config/urls.py`, `config/wsgi.py`, `config/asgi.py`
- Create: `apps/__init__.py`

- [ ] **Step 1: Install deps to Homebrew Python 3.12 (no venv) and create the project**

Run:
```bash
brew install python@3.12 mysql pkg-config   # one-time
brew services start mysql                    # start MySQL daemon
pip3.12 install --break-system-packages -r requirements.txt
python3.12 -m django startproject config .

# Create the dev database
mysql -uroot <<SQL
CREATE DATABASE merrymeal CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
CREATE USER 'merrymeal'@'localhost' IDENTIFIED BY 'merrymeal';
GRANT ALL ON merrymeal.* TO 'merrymeal'@'localhost';
FLUSH PRIVILEGES;
SQL
```

This generates `manage.py`, `config/settings.py`, `config/urls.py`, `config/wsgi.py`, `config/asgi.py`.

- [ ] **Step 2: Remove the generated `config/settings.py`**

We will replace it with a `settings/` package in Task 3.

Run: `rm config/settings.py`

- [ ] **Step 3: Create the `apps` namespace**

Run: `mkdir -p apps && touch apps/__init__.py`

- [ ] **Step 4: Verify the manage.py imports the right module**

Open `manage.py`. It should reference `config.settings`. Change the default to `config.settings.dev`:

```python
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings.dev")
```

- [ ] **Step 5: Commit**

```bash
git add manage.py config/ apps/
git commit -m "chore: initial Django project skeleton"
```

---

## Task 3: Split settings into `base` / `dev` / `prod` / `test`

**Files:**
- Create: `config/settings/__init__.py`
- Create: `config/settings/base.py`
- Create: `config/settings/dev.py`
- Create: `config/settings/prod.py`
- Create: `config/settings/test.py`

- [ ] **Step 1: Create the settings package**

```bash
mkdir -p config/settings
touch config/settings/__init__.py
```

- [ ] **Step 2: Write `config/settings/base.py`**

```python
from pathlib import Path
import environ

BASE_DIR = Path(__file__).resolve().parent.parent.parent
env = environ.Env()
environ.Env.read_env(BASE_DIR / ".env")

SECRET_KEY = env("DJANGO_SECRET_KEY", default="dev-only-secret")
DEBUG = env.bool("DJANGO_DEBUG", default=False)
ALLOWED_HOSTS = env.list("DJANGO_ALLOWED_HOSTS", default=["localhost", "127.0.0.1"])

INSTALLED_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    # Local
    "apps.core",
    "apps.accounts",
]

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "whitenoise.middleware.WhiteNoiseMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
]

ROOT_URLCONF = "config.urls"

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [BASE_DIR / "templates"],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.debug",
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
            ],
        },
    },
]

WSGI_APPLICATION = "config.wsgi.application"

DATABASES = {"default": env.db("DATABASE_URL", default="sqlite:///db.sqlite3")}

AUTH_USER_MODEL = "accounts.User"

AUTH_PASSWORD_VALIDATORS = [
    {"NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator"},
    {"NAME": "django.contrib.auth.password_validation.MinimumLengthValidator"},
    {"NAME": "django.contrib.auth.password_validation.CommonPasswordValidator"},
    {"NAME": "django.contrib.auth.password_validation.NumericPasswordValidator"},
]

LANGUAGE_CODE = "en-au"
TIME_ZONE = "Australia/Melbourne"
USE_I18N = True
USE_TZ = True

STATIC_URL = "/static/"
STATIC_ROOT = BASE_DIR / "staticfiles"
STATICFILES_DIRS = [BASE_DIR / "static" / "dist"]

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

LOGIN_URL = "accounts:login"
LOGIN_REDIRECT_URL = "/"
LOGOUT_REDIRECT_URL = "accounts:login"
```

- [ ] **Step 3: Write `config/settings/dev.py`**

```python
from .base import *  # noqa

DEBUG = True
ALLOWED_HOSTS = ["*"]
EMAIL_BACKEND = "django.core.mail.backends.console.EmailBackend"
```

- [ ] **Step 4: Write `config/settings/prod.py`**

```python
from .base import *  # noqa

DEBUG = False
SECURE_HSTS_SECONDS = 60 * 60 * 24 * 30
SECURE_HSTS_INCLUDE_SUBDOMAINS = True
SECURE_HSTS_PRELOAD = True
SECURE_SSL_REDIRECT = True
SESSION_COOKIE_SECURE = True
CSRF_COOKIE_SECURE = True
SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")
```

- [ ] **Step 5: Write `config/settings/test.py`**

```python
from .base import *  # noqa

DATABASES = {"default": {"ENGINE": "django.db.backends.sqlite3", "NAME": ":memory:"}}
PASSWORD_HASHERS = ["django.contrib.auth.hashers.MD5PasswordHasher"]
DEBUG = False
```

- [ ] **Step 6: Verify Django boots**

Run: `DJANGO_SETTINGS_MODULE=config.settings.test python3.12 -c "import django; django.setup()"`
Expected: no output, exit code 0.

- [ ] **Step 7: Commit**

```bash
git add config/settings/
git commit -m "feat(config): split settings into base/dev/prod/test"
```

---

## Task 4: Create the `core` app — `TimeStampedModel` and `SoftDeleteModel`

**Files:**
- Create: `apps/core/__init__.py`
- Create: `apps/core/apps.py`
- Create: `apps/core/managers.py`
- Create: `apps/core/models.py`
- Create: `apps/core/tests/__init__.py`
- Create: `apps/core/tests/test_models.py`

- [ ] **Step 1: Create the app skeleton**

```bash
mkdir -p apps/core/tests
touch apps/core/__init__.py apps/core/tests/__init__.py
```

- [ ] **Step 2: Write `apps/core/apps.py`**

```python
from django.apps import AppConfig


class CoreConfig(AppConfig):
    name = "apps.core"
    label = "core"
```

- [ ] **Step 3: Write the failing test `apps/core/tests/test_models.py`**

```python
import time
import pytest
from django.db import models
from apps.core.models import TimeStampedModel, SoftDeleteModel


class _StampExample(TimeStampedModel):
    name = models.CharField(max_length=20)

    class Meta:
        app_label = "core"


class _SoftExample(SoftDeleteModel):
    name = models.CharField(max_length=20)

    class Meta:
        app_label = "core"


@pytest.mark.django_db
def test_timestamped_sets_created_and_updated():
    obj = _StampExample.objects.create(name="a")
    assert obj.created_at is not None
    assert obj.updated_at is not None
    first_updated = obj.updated_at
    time.sleep(0.01)
    obj.name = "b"
    obj.save()
    assert obj.updated_at > first_updated


@pytest.mark.django_db
def test_soft_delete_excludes_from_default_manager():
    obj = _SoftExample.objects.create(name="a")
    obj.delete()
    assert obj.deleted_at is not None
    assert _SoftExample.objects.count() == 0
    assert _SoftExample.all_objects.count() == 1
```

- [ ] **Step 4: Run test to confirm it fails**

Run: `python3.12 -m pytest apps/core/tests/test_models.py -v`
Expected: ImportError — `TimeStampedModel` / `SoftDeleteModel` do not exist yet.

- [ ] **Step 5: Write `apps/core/managers.py`**

```python
from django.db import models
from django.utils import timezone


class SoftDeleteManager(models.Manager):
    def get_queryset(self):
        return super().get_queryset().filter(deleted_at__isnull=True)


class AllObjectsManager(models.Manager):
    pass
```

- [ ] **Step 6: Write `apps/core/models.py`**

```python
from django.db import models
from django.utils import timezone

from .managers import AllObjectsManager, SoftDeleteManager


class TimeStampedModel(models.Model):
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        abstract = True


class SoftDeleteModel(TimeStampedModel):
    deleted_at = models.DateTimeField(null=True, blank=True)

    objects = SoftDeleteManager()
    all_objects = AllObjectsManager()

    class Meta:
        abstract = True

    def delete(self, using=None, keep_parents=False):
        self.deleted_at = timezone.now()
        self.save(update_fields=["deleted_at", "updated_at"])
```

- [ ] **Step 7: Run test to confirm it passes**

Run: `python3.12 -m pytest apps/core/tests/test_models.py -v`
Expected: 2 passed.

- [ ] **Step 8: Commit**

```bash
git add apps/core/
git commit -m "feat(core): add TimeStampedModel and SoftDeleteModel"
```

---

## Task 5: Core — Haversine distance helper

**Files:**
- Create: `apps/core/geo.py`
- Create: `apps/core/tests/test_geo.py`

- [ ] **Step 1: Write the failing test `apps/core/tests/test_geo.py`**

```python
import math
from apps.core.geo import haversine_km


def test_haversine_known_distance_melbourne_to_sydney():
    melbourne = (-37.8136, 144.9631)
    sydney = (-33.8688, 151.2093)
    distance = haversine_km(*melbourne, *sydney)
    assert math.isclose(distance, 713, abs_tol=5)


def test_haversine_zero_distance():
    assert haversine_km(0.0, 0.0, 0.0, 0.0) == 0.0
```

- [ ] **Step 2: Run test to confirm it fails**

Run: `python3.12 -m pytest apps/core/tests/test_geo.py -v`
Expected: ImportError — `haversine_km` not defined.

- [ ] **Step 3: Write `apps/core/geo.py`**

```python
import math

EARTH_RADIUS_KM = 6371.0088


def haversine_km(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    r1, r2 = math.radians(lat1), math.radians(lat2)
    dlat = math.radians(lat2 - lat1)
    dlon = math.radians(lon2 - lon1)
    a = math.sin(dlat / 2) ** 2 + math.cos(r1) * math.cos(r2) * math.sin(dlon / 2) ** 2
    c = 2 * math.asin(math.sqrt(a))
    return EARTH_RADIUS_KM * c
```

- [ ] **Step 4: Run test to confirm it passes**

Run: `python3.12 -m pytest apps/core/tests/test_geo.py -v`
Expected: 2 passed.

- [ ] **Step 5: Commit**

```bash
git add apps/core/geo.py apps/core/tests/test_geo.py
git commit -m "feat(core): add haversine_km helper for 10 km service-radius rule"
```

---

## Task 6: Core — `@role_required` decorator

**Files:**
- Create: `apps/core/decorators.py`
- Create: `apps/core/tests/test_decorators.py`

- [ ] **Step 1: Write the failing test `apps/core/tests/test_decorators.py`**

```python
import pytest
from django.http import HttpResponse
from django.test import RequestFactory
from django.contrib.auth.models import AnonymousUser

from apps.core.decorators import role_required


@role_required("admin")
def view(request):
    return HttpResponse("ok")


@pytest.mark.django_db
def test_anonymous_user_is_redirected_to_login():
    request = RequestFactory().get("/x")
    request.user = AnonymousUser()
    response = view(request)
    assert response.status_code == 302
    assert "/accounts/login/" in response.url


@pytest.mark.django_db
def test_wrong_role_returns_403(django_user_model):
    user = django_user_model.objects.create_user(
        email="m@example.com", password="x", role="member", full_name="M"
    )
    request = RequestFactory().get("/x")
    request.user = user
    response = view(request)
    assert response.status_code == 403


@pytest.mark.django_db
def test_correct_role_allows_through(django_user_model):
    user = django_user_model.objects.create_user(
        email="a@example.com", password="x", role="admin", full_name="A"
    )
    request = RequestFactory().get("/x")
    request.user = user
    response = view(request)
    assert response.status_code == 200
```

- [ ] **Step 2: Write `apps/core/decorators.py`**

```python
from functools import wraps
from django.http import HttpResponseForbidden
from django.shortcuts import redirect
from django.urls import reverse


def role_required(*roles: str):
    def decorator(view_func):
        @wraps(view_func)
        def _wrapped(request, *args, **kwargs):
            user = request.user
            if not user.is_authenticated:
                return redirect(reverse("accounts:login"))
            if getattr(user, "role", None) not in roles:
                return HttpResponseForbidden("Forbidden")
            return view_func(request, *args, **kwargs)

        return _wrapped

    return decorator
```

- [ ] **Step 3: This test will not pass yet — `User` model and `accounts:login` URL come in later tasks.**

Skip the test run for now. We re-run in Task 9 once the User model exists.

- [ ] **Step 4: Commit**

```bash
git add apps/core/decorators.py apps/core/tests/test_decorators.py
git commit -m "feat(core): add role_required decorator (tests pending User model)"
```

---

## Task 7: Accounts — custom `User` model

**Files:**
- Create: `apps/accounts/__init__.py`
- Create: `apps/accounts/apps.py`
- Create: `apps/accounts/models.py`
- Create: `apps/accounts/admin.py`
- Create: `apps/accounts/tests/__init__.py`
- Create: `apps/accounts/tests/factories.py`
- Create: `apps/accounts/tests/test_models.py`

- [ ] **Step 1: Create the app skeleton**

```bash
mkdir -p apps/accounts/tests apps/accounts/migrations
touch apps/accounts/__init__.py apps/accounts/tests/__init__.py apps/accounts/migrations/__init__.py
```

- [ ] **Step 2: Write `apps/accounts/apps.py`**

```python
from django.apps import AppConfig


class AccountsConfig(AppConfig):
    name = "apps.accounts"
    label = "accounts"
```

- [ ] **Step 3: Write the failing test `apps/accounts/tests/test_models.py`**

```python
import pytest
from django.contrib.auth import get_user_model

User = get_user_model()


@pytest.mark.django_db
def test_user_requires_email_and_role():
    user = User.objects.create_user(
        email="a@example.com", password="pw", full_name="Alice", role="member"
    )
    assert user.email == "a@example.com"
    assert user.full_name == "Alice"
    assert user.role == "member"
    assert user.check_password("pw")
    assert user.is_active is True
    assert user.deleted_at is None


@pytest.mark.django_db
def test_email_is_unique():
    User.objects.create_user(
        email="a@example.com", password="pw", full_name="A", role="member"
    )
    with pytest.raises(Exception):
        User.objects.create_user(
            email="a@example.com", password="pw", full_name="A2", role="donor"
        )


@pytest.mark.django_db
def test_soft_delete_hides_user_from_default_manager():
    user = User.objects.create_user(
        email="a@example.com", password="pw", full_name="A", role="member"
    )
    user.delete()
    assert User.objects.filter(pk=user.pk).count() == 0
    assert User.all_objects.filter(pk=user.pk).count() == 1
```

- [ ] **Step 4: Write `apps/accounts/models.py`**

```python
from django.contrib.auth.models import AbstractBaseUser, BaseUserManager, PermissionsMixin
from django.db import models
from django.utils import timezone

from apps.core.managers import AllObjectsManager, SoftDeleteManager


class UserManager(BaseUserManager, SoftDeleteManager):
    def create_user(self, email, password, full_name, role, **extra):
        if not email:
            raise ValueError("Email is required")
        email = self.normalize_email(email)
        user = self.model(email=email, full_name=full_name, role=role, **extra)
        user.set_password(password)
        user.save(using=self._db)
        return user

    def create_superuser(self, email, password, full_name="Admin", role="admin", **extra):
        extra.setdefault("is_staff", True)
        extra.setdefault("is_superuser", True)
        return self.create_user(email, password, full_name, role, **extra)


class User(AbstractBaseUser, PermissionsMixin):
    ROLE_CHOICES = [
        ("member", "Member"),
        ("volunteer", "Volunteer"),
        ("caregiver", "Caregiver"),
        ("donor", "Donor"),
        ("kitchen_staff", "Kitchen staff"),
        ("admin", "Admin"),
    ]

    full_name = models.CharField(max_length=255)
    email = models.EmailField(unique=True)
    role = models.CharField(max_length=20, choices=ROLE_CHOICES)
    dob = models.DateField(null=True, blank=True)
    partner_id = models.BigIntegerField(null=True, blank=True)  # FK added in partners app
    is_active = models.BooleanField(default=True)
    is_staff = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    deleted_at = models.DateTimeField(null=True, blank=True)

    objects = UserManager()
    all_objects = AllObjectsManager()

    USERNAME_FIELD = "email"
    REQUIRED_FIELDS = ["full_name", "role"]

    class Meta:
        db_table = "users"

    def __str__(self) -> str:
        return f"{self.full_name} <{self.email}>"

    def delete(self, using=None, keep_parents=False):
        self.deleted_at = timezone.now()
        self.save(update_fields=["deleted_at", "updated_at"])
```

- [ ] **Step 5: Write `apps/accounts/admin.py`**

```python
from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as DjangoUserAdmin

from .models import User


@admin.register(User)
class UserAdmin(DjangoUserAdmin):
    list_display = ("email", "full_name", "role", "is_active", "created_at")
    list_filter = ("role", "is_active")
    search_fields = ("email", "full_name")
    ordering = ("email",)
    fieldsets = (
        (None, {"fields": ("email", "password")}),
        ("Personal", {"fields": ("full_name", "dob", "role")}),
        ("Permissions", {"fields": ("is_active", "is_staff", "is_superuser", "groups", "user_permissions")}),
    )
    add_fieldsets = (
        (None, {"classes": ("wide",), "fields": ("email", "full_name", "role", "password1", "password2")}),
    )
```

- [ ] **Step 6: Generate the migration**

Run: `python3.12 manage.py makemigrations accounts`
Expected: `apps/accounts/migrations/0001_initial.py` is created.

- [ ] **Step 7: Run the model tests**

Run: `python3.12 -m pytest apps/accounts/tests/test_models.py -v`
Expected: 3 passed.

- [ ] **Step 8: Now re-run the decorator tests from Task 6**

Run: `python3.12 -m pytest apps/core/tests/test_decorators.py -v`
Expected: 3 passed (URL reverse for `accounts:login` may still fail — if so, this is fixed in Task 8; skip with `-k "not test_anonymous"`).

- [ ] **Step 9: Commit**

```bash
git add apps/accounts/
git commit -m "feat(accounts): add custom User model with role + soft delete"
```

---

## Task 8: Accounts — login / logout views (mobile-first template)

**Files:**
- Create: `apps/accounts/forms.py`
- Create: `apps/accounts/views.py`
- Create: `apps/accounts/urls.py`
- Modify: `config/urls.py`
- Create: `apps/accounts/tests/test_views.py`
- Create: `templates/base.html`
- Create: `templates/accounts/login.html`
- Create: `apps/accounts/tests/factories.py`

- [ ] **Step 1: Write `apps/accounts/tests/factories.py`**

```python
import factory
from django.contrib.auth import get_user_model

User = get_user_model()


class UserFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = User
        django_get_or_create = ("email",)

    email = factory.Sequence(lambda n: f"user{n}@example.com")
    full_name = factory.Faker("name")
    role = "member"
    is_active = True

    @classmethod
    def _create(cls, model_class, *args, **kwargs):
        password = kwargs.pop("password", "pw12345!")
        user = model_class.objects.create_user(password=password, **kwargs)
        return user
```

- [ ] **Step 2: Write the failing view test `apps/accounts/tests/test_views.py`**

```python
import pytest
from django.urls import reverse

from apps.accounts.tests.factories import UserFactory


@pytest.mark.django_db
def test_login_page_renders(client):
    response = client.get(reverse("accounts:login"))
    assert response.status_code == 200
    assert b"Sign in" in response.content


@pytest.mark.django_db
def test_login_succeeds_with_correct_credentials(client):
    UserFactory(email="a@example.com", password="pw12345!")
    response = client.post(
        reverse("accounts:login"),
        {"email": "a@example.com", "password": "pw12345!"},
    )
    assert response.status_code == 302


@pytest.mark.django_db
def test_login_fails_with_wrong_password(client):
    UserFactory(email="a@example.com", password="pw12345!")
    response = client.post(
        reverse("accounts:login"),
        {"email": "a@example.com", "password": "wrong"},
    )
    assert response.status_code == 200
    assert b"Invalid" in response.content


@pytest.mark.django_db
def test_logout_redirects_to_login(client):
    user = UserFactory()
    client.force_login(user)
    response = client.post(reverse("accounts:logout"))
    assert response.status_code == 302
    assert reverse("accounts:login") in response.url
```

- [ ] **Step 3: Write `apps/accounts/forms.py`**

```python
from django import forms
from django.contrib.auth import authenticate


class EmailLoginForm(forms.Form):
    email = forms.EmailField(
        widget=forms.EmailInput(
            attrs={
                "autofocus": True,
                "autocomplete": "email",
                "inputmode": "email",
                "class": "w-full rounded-xl border-2 border-stone-300 px-4 py-4 text-lg",
                "placeholder": "you@example.com",
            }
        )
    )
    password = forms.CharField(
        widget=forms.PasswordInput(
            attrs={
                "autocomplete": "current-password",
                "class": "w-full rounded-xl border-2 border-stone-300 px-4 py-4 text-lg",
                "placeholder": "Password",
            }
        )
    )

    def clean(self):
        cleaned = super().clean()
        user = authenticate(
            email=cleaned.get("email"), password=cleaned.get("password")
        )
        if user is None:
            raise forms.ValidationError("Invalid email or password")
        cleaned["user"] = user
        return cleaned
```

- [ ] **Step 4: Write `apps/accounts/views.py`**

```python
from django.contrib.auth import login, logout
from django.http import HttpResponseRedirect
from django.shortcuts import redirect, render
from django.urls import reverse
from django.views.decorators.http import require_http_methods

from .forms import EmailLoginForm


@require_http_methods(["GET", "POST"])
def login_view(request):
    if request.user.is_authenticated:
        return redirect("/")
    if request.method == "POST":
        form = EmailLoginForm(request.POST)
        if form.is_valid():
            login(request, form.cleaned_data["user"])
            return HttpResponseRedirect(request.GET.get("next", "/"))
    else:
        form = EmailLoginForm()
    return render(request, "accounts/login.html", {"form": form})


@require_http_methods(["POST"])
def logout_view(request):
    logout(request)
    return redirect(reverse("accounts:login"))
```

- [ ] **Step 5: Write `apps/accounts/urls.py`**

```python
from django.urls import path

from . import views

app_name = "accounts"

urlpatterns = [
    path("login/", views.login_view, name="login"),
    path("logout/", views.logout_view, name="logout"),
]
```

- [ ] **Step 6: Update `config/urls.py`**

```python
from django.contrib import admin
from django.urls import include, path

urlpatterns = [
    path("admin/", admin.site.urls),
    path("accounts/", include("apps.accounts.urls")),
]
```

- [ ] **Step 7: Configure authentication backend**

Add to `config/settings/base.py` after `AUTH_USER_MODEL`:

```python
AUTHENTICATION_BACKENDS = ["apps.accounts.backends.EmailBackend"]
```

Create `apps/accounts/backends.py`:

```python
from django.contrib.auth.backends import ModelBackend
from django.contrib.auth import get_user_model


class EmailBackend(ModelBackend):
    def authenticate(self, request, email=None, password=None, **kwargs):
        UserModel = get_user_model()
        try:
            user = UserModel.objects.get(email=email)
        except UserModel.DoesNotExist:
            return None
        if user.check_password(password) and self.user_can_authenticate(user):
            return user
        return None
```

- [ ] **Step 8: Write `templates/base.html` (mobile-first shell)**

```html
{% load static %}<!DOCTYPE html>
<html lang="en" class="h-full">
  <head>
    <meta charset="utf-8" />
    <meta name="viewport" content="width=device-width, initial-scale=1, viewport-fit=cover" />
    <meta name="theme-color" content="#0f766e" />
    <title>{% block title %}MerryMeal{% endblock %}</title>
    <link rel="stylesheet" href="{% static 'output.css' %}" />
    <script src="https://unpkg.com/htmx.org@1.9.12" defer></script>
    <script src="https://unpkg.com/alpinejs@3.14.1" defer></script>
  </head>
  <body class="h-full bg-stone-50 text-stone-900 antialiased">
    <main class="mx-auto flex min-h-full max-w-md flex-col px-4 py-6">
      {% block content %}{% endblock %}
    </main>
  </body>
</html>
```

- [ ] **Step 9: Write `templates/accounts/login.html`**

```html
{% extends "base.html" %}
{% block title %}Sign in · MerryMeal{% endblock %}
{% block content %}
<section class="mt-8 flex flex-col gap-6">
  <header class="text-center">
    <h1 class="text-3xl font-semibold tracking-tight">Sign in</h1>
    <p class="mt-2 text-stone-600">Welcome back to MerryMeal.</p>
  </header>

  <form method="post" class="flex flex-col gap-4" novalidate>
    {% csrf_token %}
    {% if form.non_field_errors %}
      <div class="rounded-xl bg-red-50 px-4 py-3 text-red-800" role="alert">
        {{ form.non_field_errors.0 }}
      </div>
    {% endif %}

    <label class="flex flex-col gap-1 text-sm font-medium">
      Email
      {{ form.email }}
    </label>

    <label class="flex flex-col gap-1 text-sm font-medium">
      Password
      {{ form.password }}
    </label>

    <button type="submit"
            class="mt-2 min-h-[48px] rounded-xl bg-teal-700 px-4 py-3 text-lg font-semibold text-white active:bg-teal-800">
      Sign in
    </button>
  </form>
</section>
{% endblock %}
```

- [ ] **Step 10: Run the view tests**

Run: `python3.12 -m pytest apps/accounts/tests/test_views.py -v`
Expected: 4 passed.

- [ ] **Step 11: Commit**

```bash
git add apps/accounts/ templates/ config/urls.py config/settings/base.py
git commit -m "feat(accounts): add mobile-first login/logout flow with email backend"
```

---

## Task 9: Tailwind build pipeline

**Files:**
- Create: `package.json`
- Create: `tailwind.config.js`
- Create: `static/src/input.css`

- [ ] **Step 1: Write `package.json`**

```json
{
  "name": "merrymeal",
  "private": true,
  "scripts": {
    "build:css": "tailwindcss -i ./static/src/input.css -o ./static/dist/output.css --minify",
    "watch:css": "tailwindcss -i ./static/src/input.css -o ./static/dist/output.css --watch"
  },
  "devDependencies": {
    "tailwindcss": "^3.4.0"
  }
}
```

- [ ] **Step 2: Write `tailwind.config.js`**

```javascript
module.exports = {
  content: [
    "./templates/**/*.html",
    "./apps/**/templates/**/*.html",
  ],
  theme: {
    extend: {
      fontFamily: {
        sans: ['system-ui', '-apple-system', 'Segoe UI', 'Roboto', 'sans-serif'],
      },
    },
  },
  plugins: [],
};
```

- [ ] **Step 3: Write `static/src/input.css`**

```css
@tailwind base;
@tailwind components;
@tailwind utilities;

@layer base {
  html { font-size: 18px; }
  button, [role="button"] { min-height: 44px; }
}
```

- [ ] **Step 4: Install and build**

Run:
```bash
npm install
npm run build:css
```
Expected: `static/dist/output.css` exists.

- [ ] **Step 5: Verify a page renders with styles**

Run: `python3.12 manage.py runserver` and `curl -s http://localhost:8000/accounts/login/ | grep "rounded-xl"`
Expected: HTML contains Tailwind classes.

- [ ] **Step 6: Commit**

```bash
git add package.json tailwind.config.js static/src/
git commit -m "feat(ui): set up Tailwind CSS build pipeline (mobile-first base)"
```

---

## Task 10: pytest configuration

**Files:**
- Create: `pytest.ini`
- Create: `conftest.py`

- [ ] **Step 1: Write `pytest.ini`**

```ini
[pytest]
DJANGO_SETTINGS_MODULE = config.settings.test
python_files = test_*.py
python_classes = Test*
python_functions = test_*
addopts = -ra --strict-markers
testpaths = apps tests
```

- [ ] **Step 2: Write top-level `conftest.py`**

```python
import pytest


@pytest.fixture(autouse=True)
def _media_root(tmp_path, settings):
    settings.MEDIA_ROOT = tmp_path / "media"
```

- [ ] **Step 3: Run the full suite**

Run: `python3.12 -m pytest -v`
Expected: all previously written tests pass, no DJANGO_SETTINGS_MODULE warning.

- [ ] **Step 4: Commit**

```bash
git add pytest.ini conftest.py
git commit -m "test: configure pytest-django for full suite"
```

---

## Task 11: Docker Compose stack

**Files:**
- Create: `Dockerfile`
- Create: `compose.yaml`

- [ ] **Step 1: Write `Dockerfile`**

```dockerfile
FROM python:3.12-slim AS base
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1

WORKDIR /app
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential default-libmysqlclient-dev pkg-config \
 && rm -rf /var/lib/apt/lists/*

COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt

COPY . .
EXPOSE 8000
CMD ["gunicorn", "config.wsgi:application", "--bind", "0.0.0.0:8000"]
```

- [ ] **Step 2: Write `compose.yaml`**

```yaml
services:
  db:
    image: mysql:8.0
    environment:
      MYSQL_ROOT_PASSWORD: rootpw
      MYSQL_DATABASE: merrymeal
      MYSQL_USER: merrymeal
      MYSQL_PASSWORD: merrymeal
    volumes:
      - dbdata:/var/lib/mysql
    healthcheck:
      test: ["CMD", "mysqladmin", "ping", "-h", "localhost"]
      interval: 5s
      retries: 10

  redis:
    image: redis:7-alpine
    healthcheck:
      test: ["CMD", "redis-cli", "ping"]
      interval: 5s
      retries: 5

  web:
    build: .
    command: python manage.py runserver 0.0.0.0:8000
    environment:
      DJANGO_SETTINGS_MODULE: config.settings.dev
      DATABASE_URL: mysql://merrymeal:merrymeal@db:3306/merrymeal
      REDIS_URL: redis://redis:6379/0
    volumes:
      - .:/app
    ports:
      - "8000:8000"
    depends_on:
      db: { condition: service_healthy }
      redis: { condition: service_healthy }

  worker:
    build: .
    command: python manage.py qcluster
    environment:
      DJANGO_SETTINGS_MODULE: config.settings.dev
      DATABASE_URL: mysql://merrymeal:merrymeal@db:3306/merrymeal
      REDIS_URL: redis://redis:6379/0
    volumes:
      - .:/app
    depends_on:
      db: { condition: service_healthy }
      redis: { condition: service_healthy }

volumes:
  dbdata:
```

- [ ] **Step 3: Bring the stack up**

Run: `docker compose up -d db redis web`
Wait until `web` is listening on `:8000`.

- [ ] **Step 4: Apply migrations inside the container**

Run: `docker compose exec web python manage.py migrate`
Expected: migrations applied with no error.

- [ ] **Step 5: Smoke-test the login page**

Run: `curl -s -o /dev/null -w "%{http_code}\n" http://localhost:8000/accounts/login/`
Expected: `200`.

- [ ] **Step 6: Commit**

```bash
git add Dockerfile compose.yaml
git commit -m "feat(infra): docker compose for web, mysql, redis, worker"
```

---

## Task 12: Playwright mobile-viewport smoke test

**Files:**
- Create: `playwright_config.py`
- Create: `tests_e2e/__init__.py`
- Create: `tests_e2e/conftest.py`
- Create: `tests_e2e/test_smoke_login.py`

- [ ] **Step 1: Install Playwright browsers**

Run: `python3.12 -m playwright install chromium`

- [ ] **Step 2: Write `playwright_config.py` (note: underscore, not dot — Python module rules)**

```python
DEVICE = {
    "viewport": {"width": 375, "height": 812},
    "device_scale_factor": 3,
    "is_mobile": True,
    "has_touch": True,
    "user_agent": "Mozilla/5.0 (iPhone; CPU iPhone OS 17_0 like Mac OS X) AppleWebKit/605.1.15",
}
```

- [ ] **Step 3: Write `tests_e2e/conftest.py`**

```python
import pytest
from playwright.sync_api import sync_playwright

from playwright_config import DEVICE


@pytest.fixture(scope="session")
def browser():
    with sync_playwright() as p:
        browser = p.chromium.launch()
        yield browser
        browser.close()


@pytest.fixture
def page(browser):
    context = browser.new_context(**DEVICE)
    page = context.new_page()
    yield page
    context.close()
```

- [ ] **Step 4: Write `tests_e2e/test_smoke_login.py`**

```python
def test_login_page_renders_at_mobile_viewport(page):
    page.goto("http://localhost:8000/accounts/login/")
    assert "Sign in" in page.title()
    button = page.locator("button:has-text('Sign in')")
    box = button.bounding_box()
    assert box["height"] >= 44, "Sign in button below 44px touch target"
```

- [ ] **Step 5: Run E2E smoke test against the running stack**

Run: `python3.12 -m pytest tests_e2e/ -v`
Expected: 1 passed.

- [ ] **Step 6: Commit**

```bash
git add playwright_config.py tests_e2e/
git commit -m "test(e2e): playwright mobile-viewport smoke test for login"
```

---

## Task 12b: Password reset flow (Django built-ins)

**Files:**
- Modify: `apps/accounts/urls.py`
- Create: `templates/accounts/password_reset_form.html`
- Create: `templates/accounts/password_reset_done.html`
- Create: `templates/accounts/password_reset_confirm.html`
- Create: `templates/accounts/password_reset_complete.html`
- Create: `templates/accounts/password_reset_email.html`
- Create: `apps/accounts/tests/test_password_reset.py`

- [ ] **Step 1: Write the failing test**

```python
import pytest
from django.core import mail
from django.urls import reverse

from apps.accounts.tests.factories import UserFactory


@pytest.mark.django_db
def test_password_reset_sends_email(client):
    UserFactory(email="reset@example.com")
    response = client.post(
        reverse("accounts:password_reset"),
        {"email": "reset@example.com"},
    )
    assert response.status_code == 302
    assert len(mail.outbox) == 1
    assert "reset@example.com" in mail.outbox[0].to


@pytest.mark.django_db
def test_password_reset_form_renders(client):
    response = client.get(reverse("accounts:password_reset"))
    assert response.status_code == 200
    assert b"Reset password" in response.content
```

- [ ] **Step 2: Run test to confirm it fails**

Run: `python3.12 -m pytest apps/accounts/tests/test_password_reset.py -v`
Expected: NoReverseMatch — `accounts:password_reset` does not exist.

- [ ] **Step 3: Update `apps/accounts/urls.py`**

```python
from django.contrib.auth import views as auth_views
from django.urls import path, reverse_lazy

from . import views

app_name = "accounts"

urlpatterns = [
    path("login/", views.login_view, name="login"),
    path("logout/", views.logout_view, name="logout"),
    path(
        "password_reset/",
        auth_views.PasswordResetView.as_view(
            template_name="accounts/password_reset_form.html",
            email_template_name="accounts/password_reset_email.html",
            success_url=reverse_lazy("accounts:password_reset_done"),
        ),
        name="password_reset",
    ),
    path(
        "password_reset/done/",
        auth_views.PasswordResetDoneView.as_view(
            template_name="accounts/password_reset_done.html"
        ),
        name="password_reset_done",
    ),
    path(
        "reset/<uidb64>/<token>/",
        auth_views.PasswordResetConfirmView.as_view(
            template_name="accounts/password_reset_confirm.html",
            success_url=reverse_lazy("accounts:password_reset_complete"),
        ),
        name="password_reset_confirm",
    ),
    path(
        "reset/done/",
        auth_views.PasswordResetCompleteView.as_view(
            template_name="accounts/password_reset_complete.html"
        ),
        name="password_reset_complete",
    ),
]
```

- [ ] **Step 4: Write `templates/accounts/password_reset_form.html`**

```html
{% extends "base.html" %}
{% block title %}Reset password · MerryMeal{% endblock %}
{% block content %}
<section class="mt-8 flex flex-col gap-6">
  <h1 class="text-3xl font-semibold">Reset password</h1>
  <p class="text-stone-600">Enter your email and we'll send you a reset link.</p>
  <form method="post" class="flex flex-col gap-4">
    {% csrf_token %}
    <input type="email" name="email" required autofocus
           class="w-full rounded-xl border-2 border-stone-300 px-4 py-4 text-lg"
           placeholder="you@example.com" />
    <button type="submit"
            class="min-h-[48px] rounded-xl bg-teal-700 px-4 py-3 text-lg font-semibold text-white">
      Send reset link
    </button>
  </form>
</section>
{% endblock %}
```

- [ ] **Step 5: Write `templates/accounts/password_reset_done.html`**

```html
{% extends "base.html" %}
{% block title %}Check your email · MerryMeal{% endblock %}
{% block content %}
<section class="mt-8 flex flex-col gap-4 text-center">
  <h1 class="text-3xl font-semibold">Check your email</h1>
  <p class="text-stone-600">If an account exists for that email, we've sent a reset link.</p>
</section>
{% endblock %}
```

- [ ] **Step 6: Write `templates/accounts/password_reset_confirm.html`**

```html
{% extends "base.html" %}
{% block title %}Set new password · MerryMeal{% endblock %}
{% block content %}
<section class="mt-8 flex flex-col gap-6">
  <h1 class="text-3xl font-semibold">Set new password</h1>
  {% if validlink %}
    <form method="post" class="flex flex-col gap-4">
      {% csrf_token %}
      {{ form.as_p }}
      <button type="submit"
              class="min-h-[48px] rounded-xl bg-teal-700 px-4 py-3 text-lg font-semibold text-white">
        Change password
      </button>
    </form>
  {% else %}
    <p class="text-red-700">This reset link is invalid or expired.</p>
  {% endif %}
</section>
{% endblock %}
```

- [ ] **Step 7: Write `templates/accounts/password_reset_complete.html`**

```html
{% extends "base.html" %}
{% block title %}Password reset · MerryMeal{% endblock %}
{% block content %}
<section class="mt-8 flex flex-col gap-4 text-center">
  <h1 class="text-3xl font-semibold">Password reset</h1>
  <p class="text-stone-600">You can now <a class="text-teal-700 underline" href="{% url 'accounts:login' %}">sign in</a>.</p>
</section>
{% endblock %}
```

- [ ] **Step 8: Write `templates/accounts/password_reset_email.html`**

```
Hi,

You requested a password reset for your MerryMeal account.

Click the link below to set a new password:
{{ protocol }}://{{ domain }}{% url 'accounts:password_reset_confirm' uidb64=uid token=token %}

If you didn't request this, ignore this email.

— MerryMeal
```

- [ ] **Step 9: Run the tests**

Run: `python3.12 -m pytest apps/accounts/tests/test_password_reset.py -v`
Expected: 2 passed.

- [ ] **Step 10: Commit**

```bash
git add apps/accounts/urls.py templates/accounts/password_reset_*.html apps/accounts/tests/test_password_reset.py
git commit -m "feat(accounts): mobile-first password reset flow"
```

---

## Task 13: GitHub Actions CI

**Files:**
- Create: `.github/workflows/ci.yaml`

- [ ] **Step 1: Write `.github/workflows/ci.yaml`**

```yaml
name: CI
on:
  push: { branches: [main] }
  pull_request:

jobs:
  test:
    runs-on: ubuntu-latest
    services:
      mysql:
        image: mysql:8.0
        env:
          MYSQL_ROOT_PASSWORD: root
          MYSQL_DATABASE: merrymeal
          MYSQL_USER: merrymeal
          MYSQL_PASSWORD: merrymeal
        ports: ["3306:3306"]
        options: >-
          --health-cmd="mysqladmin ping" --health-interval=5s --health-timeout=5s --health-retries=10
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with: { python-version: "3.12" }
      - uses: actions/setup-node@v4
        with: { node-version: "20" }
      - name: Install Python deps
        run: |
          python -m pip install --upgrade pip
          pip install -r requirements.txt
      - name: Install Node deps + build CSS
        run: |
          npm ci
          npm run build:css
      - name: Lint
        run: ruff check .
      - name: Unit tests
        env:
          DATABASE_URL: mysql://merrymeal:merrymeal@127.0.0.1:3306/merrymeal
        run: pytest apps/ -v
      - name: Install Playwright
        run: python -m playwright install --with-deps chromium
      - name: E2E smoke
        env:
          DJANGO_SETTINGS_MODULE: config.settings.dev
          DATABASE_URL: mysql://merrymeal:merrymeal@127.0.0.1:3306/merrymeal
        run: |
          python manage.py migrate
          python manage.py runserver 0.0.0.0:8000 &
          sleep 3
          pytest tests_e2e/ -v
```

- [ ] **Step 2: Commit**

```bash
git add .github/workflows/ci.yaml
git commit -m "ci: ruff + pytest + playwright workflow"
```

---

## Task 14: README quickstart

**Files:**
- Create: `README.md`

- [ ] **Step 1: Write `README.md`**

```markdown
# MerryMeal

Charity meal-delivery platform — Django 5, mobile-first.

## Quickstart

```bash
cp .env.example .env
docker compose up -d
docker compose exec web python manage.py migrate
docker compose exec web python manage.py createsuperuser
npm install && npm run build:css
open http://localhost:8000/accounts/login/
```

## Tests

```bash
pytest apps/                # unit
pytest tests_e2e/           # mobile-viewport smoke
ruff check .                # lint
```

## Docs

- Roadmap: `docs/superpowers/specs/2026-06-01-merrymeal-django-design.md`
- Phase 0 plan (this milestone): `docs/superpowers/plans/2026-06-01-phase-0-foundation.md`
```

- [ ] **Step 2: Commit**

```bash
git add README.md
git commit -m "docs: README quickstart"
```

---

## Definition of done (Phase 0)

- [ ] `docker compose up` brings up web, db, redis, worker.
- [ ] `pytest apps/` passes (core + accounts unit tests).
- [ ] `pytest tests_e2e/` passes (mobile-viewport smoke).
- [ ] `ruff check .` passes.
- [ ] CI is green on `main`.
- [ ] Login page renders at 375 px with 44 px touch targets.
- [ ] Custom `User` model works in Django admin (`/admin/`).
- [ ] All 15 task commits land on `main` (Tasks 1–12, 12b, 13, 14).

Once green, the next brainstorm is **Phase 1 — Identity & onboarding** (caregivers, partners, dietary, public apply flow).
