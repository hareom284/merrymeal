"""Template context processors registered in ``config/settings/base.py``.

Two responsibilities, both injected into every authenticated template:

1. ``nav_items`` — the role-keyed sidebar/bottom-nav list driven by
   ``apps.dashboards.services.navigation``.
2. ``notifications_url`` + ``notifications_unread`` — so the bell in
   ``app_base.html`` stays role-agnostic. Each role gets its own
   feed (members get the synthesised member feed; admins get the
   attention-counts feed); other roles get no bell.
"""
from django.urls import NoReverseMatch, reverse

from apps.dashboards.services.navigation import get_nav_items

# Role -> named URL of the notifications page for that role. Roles
# missing from this map don't see a bell in the topbar.
_NOTIFICATION_URL_NAME_BY_ROLE = {
    "member": "dashboards:notifications",
    "caregiver": "dashboards:notifications",
    "admin": "dashboards:admin_notifications",
}


def _admin_unread_count() -> int:
    """Wrapped in a helper so the import stays lazy — the admin
    summary service touches several model layers and we don't want to
    pay that cost on every anonymous request."""
    from apps.dashboards.services.admin_notifications import admin_notification_count

    return admin_notification_count()


def navigation(request):
    user = getattr(request, "user", None)
    nav_items = get_nav_items(user)

    notifications_url: str | None = None
    notifications_unread = 0

    if user is not None and getattr(user, "is_authenticated", False):
        url_name = _NOTIFICATION_URL_NAME_BY_ROLE.get(getattr(user, "role", None))
        if url_name:
            try:
                notifications_url = reverse(url_name)
            except NoReverseMatch:
                notifications_url = None
        if user.role == "admin":
            notifications_unread = _admin_unread_count()

    return {
        "nav_items": nav_items,
        "notifications_url": notifications_url,
        "notifications_unread": notifications_unread,
    }
