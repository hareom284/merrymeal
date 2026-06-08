"""Donations URL conf.

Re-exports the donate URL patterns so ``include("apps.donations.urls")``
works from ``config/urls.py``. As more donation flows land (Story 5.4
Stripe webhook, Story 5.5 thanks page, Story 5.7 manage page) they get
their own module under ``apps/donations/urls/`` and are merged here.
"""

from apps.donations.urls.donate import app_name, urlpatterns

__all__ = ["app_name", "urlpatterns"]
