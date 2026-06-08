from django.urls import include, path

# Django's built-in admin is intentionally NOT mounted.
# All operational/admin UIs are built as custom views under /
# (e.g. /admin/applications/, /admin/kitchens/) using the brand design.
# Data management via CLI: `python3 manage.py shell`, `createsuperuser`,
# custom management commands.

urlpatterns = [
    path("", include("apps.accounts.urls")),
    path("", include("apps.dashboards.urls")),
    path("admin/planner/", include("apps.planning.urls")),
    path("kitchen/", include("apps.kitchens.urls")),
    path("kitchen/safety/", include("apps.food_safety.urls")),
    path("volunteer/", include("apps.volunteers.urls")),
    # Story 4.14 — ``apps.delivery.urls`` now carries its own
    # ``volunteer/`` and ``admin/`` prefixes inside the module so the
    # volunteer-facing screens (Stories 4.8 / 4.12) and the admin
    # reassign widget (Story 4.14) share one ``delivery`` namespace.
    path("", include("apps.delivery.urls")),
    # Story 5.4 — donations app routes (Stripe webhook). Mounted at the
    # project root so ``/stripe/webhook/`` matches the URL we configure
    # in the Stripe dashboard. Future stories (5.3 donate page, 5.5
    # thanks page) append to ``apps/donations/urls.py``.
    path("", include("apps.donations.urls")),
]
