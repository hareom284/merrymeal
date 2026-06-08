from .base import *  # noqa: F401, F403
from .base import env

DEBUG = True
ALLOWED_HOSTS = ["*"]

# Default to the console backend in dev so emails dump to the runserver
# terminal without needing SMTP creds. Set EMAIL_BACKEND in .env to override
# (e.g. point at Mailpit on localhost:1025, or real Gmail SMTP).
EMAIL_BACKEND = env(
    "EMAIL_BACKEND",
    default="django.core.mail.backends.console.EmailBackend",
)
