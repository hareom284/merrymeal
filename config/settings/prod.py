from .base import *  # noqa: F401, F403
from .base import INSTALLED_APPS, env

DEBUG = False

# Story 4.9 — POD photo storage. Prod uploads JPEGs to S3 via
# django-storages; dev/test keep the default FileSystemStorage so CI
# never needs AWS creds. The bucket name + region + IAM creds are read
# from env in base.py; this module only flips the storage backend.
INSTALLED_APPS = INSTALLED_APPS + ["storages"]
DEFAULT_FILE_STORAGE = "storages.backends.s3boto3.S3Boto3Storage"

SECURE_HSTS_SECONDS = env.int("DJANGO_SECURE_HSTS_SECONDS", default=60 * 60 * 24 * 30)
SECURE_HSTS_INCLUDE_SUBDOMAINS = env.bool(
    "DJANGO_SECURE_HSTS_INCLUDE_SUBDOMAINS", default=True
)
SECURE_HSTS_PRELOAD = env.bool("DJANGO_SECURE_HSTS_PRELOAD", default=True)
SECURE_SSL_REDIRECT = env.bool("DJANGO_SECURE_SSL_REDIRECT", default=True)
SESSION_COOKIE_SECURE = env.bool("DJANGO_SESSION_COOKIE_SECURE", default=True)
CSRF_COOKIE_SECURE = env.bool("DJANGO_CSRF_COOKIE_SECURE", default=True)

# Nginx terminates TLS and sets X-Forwarded-Proto; Django needs this to
# trust the proxy when evaluating request.is_secure() and the SSL redirect.
SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")
