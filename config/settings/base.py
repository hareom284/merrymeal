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
    # Third-party
    "auditlog",
    "django_q",
    # Local
    "apps.core",
    "apps.accounts",
    "apps.partners",
    "apps.dietary",
    "apps.dashboards",
    "apps.kitchens",
    "apps.meals",
    "apps.planning",
    "apps.food_safety",
    "apps.volunteers",
    "apps.delivery",
    "apps.donations",
    "apps.ai_assistant",
    "apps.site_config",
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
                "apps.dashboards.context_processors.navigation",
                "apps.site_config.context_processors.org",
            ],
        },
    },
]

WSGI_APPLICATION = "config.wsgi.application"

DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.mysql",
        "NAME": env("MYSQL_DATABASE", default="merrymeal"),
        "USER": env("MYSQL_USER", default="merrymeal"),
        "PASSWORD": env("MYSQL_PASSWORD", default="merrymeal"),
        "HOST": env("MYSQL_HOST", default="localhost"),
        "PORT": env("MYSQL_PORT", default="3306"),
        "OPTIONS": {"charset": "utf8mb4"},
    }
}

AUTH_USER_MODEL = "accounts.User"

AUTHENTICATION_BACKENDS = ["apps.accounts.backends.EmailBackend"]

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
STATICFILES_DIRS = [BASE_DIR / "static"]

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

SITE_URL = env("SITE_URL", default="http://localhost:8000")

# Email — read from env so the same code path works in dev (console default),
# local SMTP (Mailpit), and prod (Gmail / SendGrid / SES). Switch implicit-SSL
# vs STARTTLS by setting the port + matching EMAIL_USE_SSL / EMAIL_USE_TLS:
#   port 465 → EMAIL_USE_SSL=True,  EMAIL_USE_TLS=False
#   port 587 → EMAIL_USE_SSL=False, EMAIL_USE_TLS=True
EMAIL_BACKEND = env(
    "EMAIL_BACKEND",
    default="django.core.mail.backends.smtp.EmailBackend",
)
EMAIL_HOST = env("EMAIL_HOST", default="localhost")
EMAIL_PORT = env.int("EMAIL_PORT", default=25)
EMAIL_HOST_USER = env("EMAIL_HOST_USER", default="")
EMAIL_HOST_PASSWORD = env("EMAIL_HOST_PASSWORD", default="")
EMAIL_USE_TLS = env.bool("EMAIL_USE_TLS", default=False)
EMAIL_USE_SSL = env.bool("EMAIL_USE_SSL", default=False)
EMAIL_TIMEOUT = env.int("EMAIL_TIMEOUT", default=10)
DEFAULT_FROM_EMAIL = env("DEFAULT_FROM_EMAIL", default="no-reply@merrymeal.local")
SERVER_EMAIL = env("SERVER_EMAIL", default=DEFAULT_FROM_EMAIL)

# LOGIN_URL = "accounts:login"
LOGIN_REDIRECT_URL = "/"
LOGOUT_REDIRECT_URL = "accounts:login"

# Media / file storage. Story 4.9 (POD photos) writes JPEGs to S3 in
# prod and ``media/`` on disk in dev. The S3 environment variables are
# read here so the env-example audit (scripts/check_env_example.py)
# stays happy in every environment; the actual ``DEFAULT_FILE_STORAGE``
# swap to django-storages happens in ``config/settings/prod.py`` (so
# CI / dev never need real AWS creds).
MEDIA_URL = env("MEDIA_URL", default="/media/")
MEDIA_ROOT = env("MEDIA_ROOT", default=str(BASE_DIR / "media"))

AWS_STORAGE_BUCKET_NAME = env("AWS_S3_BUCKET", default="")
AWS_S3_REGION_NAME = env("AWS_S3_REGION", default="ap-southeast-2")
AWS_ACCESS_KEY_ID = env("AWS_ACCESS_KEY_ID", default="")
AWS_SECRET_ACCESS_KEY = env("AWS_SECRET_ACCESS_KEY", default="")
# AWS deprecated bucket ACLs for buckets created after April 2023, so
# we must NOT send an ACL on upload. ``None`` (not the string "private")
# is the django-storages contract for "omit the header entirely".
AWS_DEFAULT_ACL = None
AWS_QUERYSTRING_AUTH = False
AWS_S3_FILE_OVERWRITE = False

# SMS — Story 4.13. The ``console`` backend (apps.core.services.sms_backends.
# ConsoleBackend) appends messages to ``apps.core.testing.sms_outbox`` and
# echoes them to stdout. ``twilio`` makes a real REST call and is only
# enabled in prod (see config/settings/prod.py).
SMS_BACKEND = env("SMS_BACKEND", default="console")
# Email address that receives the failure alert when a member has no
# linked caregiver — Story 4.13 fallback.
OFFICE_ALERT_EMAIL = env("OFFICE_ALERT_EMAIL", default="office@merrymeal.org")
# Phone number rendered in the failure alert templates ("Call the office
# on …"). Kept as a setting so the prod ops line can rotate without a
# template change.
OFFICE_PHONE = env("OFFICE_PHONE", default="03 9000 0000")
# Twilio credentials (prod only). Defaults keep dev / CI bootable
# without secrets; the TwilioBackend will fail loudly at send time if
# they remain blank in a prod environment.
TWILIO_ACCOUNT_SID = env("TWILIO_ACCOUNT_SID", default="")
TWILIO_AUTH_TOKEN = env("TWILIO_AUTH_TOKEN", default="")
TWILIO_FROM = env("TWILIO_FROM", default="")

# Stripe (Story 5.4 — Checkout integration).
#
# The publishable key is fine to expose to the browser; the secret key
# and the webhook secret are server-side only and must never leak. The
# defaults are deliberately obvious placeholder values so a missing
# ``.env`` in prod fails the first Stripe call instead of silently
# charging the wrong account.
#
# ``stripe`` is **not** pip-installed on dev / CI. The donations service
# (apps.donations.services.stripe_checkout) and webhook view defer the
# ``import stripe`` to call-time, mirroring the Twilio pattern above so
# the module graph still imports cleanly without the wheel.
STRIPE_PUBLISHABLE_KEY = env("STRIPE_PUBLISHABLE_KEY", default="pk_test_replace_me")
STRIPE_SECRET_KEY = env("STRIPE_SECRET_KEY", default="sk_test_replace_me")
STRIPE_WEBHOOK_SECRET = env("STRIPE_WEBHOOK_SECRET", default="whsec_test_only")
STRIPE_LIVE_MODE = False

# Donations — currency + redirect targets pulled from settings so a
# future market switch (NZD, GBP…) is a one-line change.
DONATIONS_CURRENCY = "aud"
DONATIONS_SUCCESS_URL = "/donate/thanks/?session_id={CHECKOUT_SESSION_ID}"
DONATIONS_CANCEL_URL = "/donate/?cancelled=1"

# Donor-impact conversion (Story 5.6). The donate-page chips, thanks
# page and receipt email render "your $X = N meals" using this knob.
# Default 300c ($3) matches the charity's per-portion cost (cooked-meal
# CoGS / portion served — see Sprint 09 brief). Overridable in ops
# without a deploy.
MEAL_COST_CENTS = env.int("MEAL_COST_CENTS", default=300)

# Receipt email (Story 5.5). ``DONATIONS_FROM_EMAIL`` is the From address
# stamped on the transactional receipt sent when a Donation flips to
# ``completed``; the ABN + address are the ATO-mandated charity details
# rendered in the body so the receipt qualifies as a tax-deductible gift
# record. Defaults are placeholder text — every prod environment MUST
# override via .env before the first live charge or donors get bogus ABN
# data on their tax records.
DONATIONS_FROM_EMAIL = env(
    "DONATIONS_FROM_EMAIL",
    default="receipts@merrymeal.org.au",
)
DONATIONS_CHARITY_ABN = env(
    "DONATIONS_CHARITY_ABN",
    default="12 345 678 901",
)
DONATIONS_CHARITY_ADDRESS = env(
    "DONATIONS_CHARITY_ADDRESS",
    default="PO Box 1, Melbourne VIC 3000",
)

# FY tax receipt (Story 6.4 — printer-friendly per-donor FY receipt
# at ``/donor/receipts/<fy>/``). These are the same data points the
# email receipt above carries, but the donor-facing FY page renders
# them as the page footer and the JSON-format endpoint exposes them
# under ``charity.abn`` / ``charity.address`` for accountants ingesting
# the response. Defaulting to the existing ``DONATIONS_CHARITY_*``
# values keeps the two surfaces in lockstep until Story 7.x replaces
# both with the real ABN/address from the accountant.
MERRYMEAL_ABN = env(
    "MERRYMEAL_ABN",
    default=DONATIONS_CHARITY_ABN,
)
MERRYMEAL_ADDRESS = env(
    "MERRYMEAL_ADDRESS",
    default=DONATIONS_CHARITY_ADDRESS,
)


# Django-Q2 cluster. We only set the knobs needed to silence the
# ``Retry and timeout are misconfigured`` warning emitted on every
# ``manage.py`` call when the defaults disagree — ``retry`` MUST be
# strictly greater than ``timeout`` or the cluster requeues the same
# task before its first run finishes. The dispatch jobs (Story 4.5
# generate, 4.6 routes) finish in <30s on a real DB; 60s timeout +
# 90s retry gives a comfortable margin without keeping a failed task
# in flight too long. Test settings override to ``sync=True`` and
# never reach this code path.
Q_CLUSTER = {
    "name": "merrymeal",
    "orm": "default",
    "timeout": 60,
    "retry": 90,
    "workers": 2,
    "recycle": 500,
    "save_limit": 250,
    "queue_limit": 50,
    "label": "Django Q",
}

# Mapbox Static Images API token (Story 12.7 — the member track-delivery
# page renders an <img> against this token). Leave unset in dev/test so
# ``static_map_url`` returns ``None`` and the template falls back to a
# stylised placeholder block — no broken images, no failing tests.
MAPBOX_TOKEN = env("MAPBOX_TOKEN", default="")

# AI assistant (Anthropic Claude). Member-facing chat widget. Leave
# the key blank to disable the widget gracefully:
# ``apps.ai_assistant.services.client.generate`` raises ClaudeUnavailable
# when the key is missing, and the view falls back to a "please call
# the office" message rather than crashing the page. Generate a key at
# https://console.anthropic.com/settings/keys (starts ``sk-ant-``).
ANTHROPIC_API_KEY = env("ANTHROPIC_API_KEY", default="")
# Claude Haiku 4.5 is the cheapest/fastest tier in the current
# generation — plenty for short factual Q&A bounded by the per-request
# data block. Bump to ``claude-sonnet-4-6`` if member replies start to
# feel sloppy; ``claude-opus-4-7`` is overkill here.
ANTHROPIC_MODEL = env("ANTHROPIC_MODEL", default="claude-haiku-4-5")
# Rate limits for the AI assistant. Both caps are enforced by
# ``apps.ai_assistant.services.rate_limit.check`` and protect the
# project's Claude spend from a runaway chat client.
#
# * ``ANTHROPIC_RATE_LIMIT_PER_USER`` — how many chat sends one user
#   can make per window. 10 is generous for a real conversation and
#   far enough below the global cap that one chatty user can't lock
#   the whole charity out.
# * ``ANTHROPIC_RATE_LIMIT_GLOBAL`` — total across all users per
#   window. 12 is a conservative ceiling that keeps spend predictable
#   on the default Claude tier.
# * ``ANTHROPIC_RATE_LIMIT_WINDOW_SECONDS`` — bucket size. The window
#   slides over the wall clock (not per-user), so the moment the
#   second hits the boundary, all counters reset.
ANTHROPIC_RATE_LIMIT_PER_USER = env.int("ANTHROPIC_RATE_LIMIT_PER_USER", default=10)
ANTHROPIC_RATE_LIMIT_GLOBAL = env.int("ANTHROPIC_RATE_LIMIT_GLOBAL", default=12)
ANTHROPIC_RATE_LIMIT_WINDOW_SECONDS = env.int(
    "ANTHROPIC_RATE_LIMIT_WINDOW_SECONDS", default=60
)
