from django.urls import include, path

from apps.core.views import manifest, service_worker

# Django's built-in admin is intentionally NOT mounted.
# All operational/admin UIs are built as custom views under /
# (e.g. /admin/applications/, /admin/kitchens/) using the brand design.
# Data management via CLI: `python3 manage.py shell`, `createsuperuser`,
# custom management commands.

urlpatterns = [
    # PWA — service worker MUST be served from the site root so its
    # scope covers every URL. Manifest matches for symmetry; see
    # apps/core/views/pwa.py for the rationale.
    path("sw.js", service_worker, name="service_worker"),
    path("manifest.webmanifest", manifest, name="manifest"),
    path("", include("apps.accounts.urls")),
    # Story 5.8 — admin campaign-progress card lives at /admin/campaigns/.
    # Included *before* the generic dashboards URLs so the namespace
    # ``dashboards_admin_campaigns`` resolves cleanly and the slug capture
    # never collides with the dashboards admin sub-include
    # (/admin/applications/, /admin/kitchens/).
    path(
        "admin/campaigns/",
        include("apps.dashboards.urls.admin_campaigns"),
    ),
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
    # Story 6.7 — public ``/partners/refer/`` form for charity
    # social workers to submit referrals on behalf of a member.
    path("partners/", include("apps.accounts.urls.partner_referral")),
    # Sprint 09 — donations app routes. Mounted at the project root so
    # ``/stripe/webhook/`` (Story 5.4) matches the URL we configure in
    # the Stripe dashboard; the donate / impact / thanks / manage routes
    # carry their own ``donate/`` and ``donations/`` prefixes inside the
    # module so the namespace stays single-rooted under ``donations:``.
    path("", include("apps.donations.urls")),
    # AI assistant — Gemini-backed chat widget endpoint.
    path("", include("apps.ai_assistant.urls")),
    # Site config — admin-editable charity name/address/phone/logo
    # at /admin/settings/.
    path("admin/", include("apps.site_config.urls")),
]

# Custom error handlers — branded 400 / 403 / 404 / 500 pages.
handler400 = "apps.site_config.views.errors.bad_request_view"
handler403 = "apps.site_config.views.errors.permission_denied_view"
handler404 = "apps.site_config.views.errors.not_found_view"
handler500 = "apps.site_config.views.errors.server_error_view"
