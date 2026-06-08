from .base import *  # noqa: F401, F403

DATABASES = {"default": {"ENGINE": "django.db.backends.sqlite3", "NAME": ":memory:"}}
PASSWORD_HASHERS = ["django.contrib.auth.hashers.MD5PasswordHasher"]
DEBUG = False

Q_CLUSTER = {"sync": True, "orm": "default"}

# Story 4.13 — force the in-memory ``console`` SMS backend so tests
# never reach out to Twilio. The console backend appends to
# ``apps.core.testing.sms_outbox`` which tests assert against.
SMS_BACKEND = "console"
