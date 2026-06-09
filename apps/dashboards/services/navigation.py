"""Per-role navigation config for the app shell.

Sidebar (desktop) and bottom tab bar (mobile) both render from the same
list. To add a menu item for a role, append a ``NavItem`` to that role's
list below — the template loops over whatever is returned by
:func:`get_nav_items`. Icons must exist in
``templates/_partials/nav_icon.html``.

Only URL names that actually resolve belong here. Dead ``href="#"``
entries previously hardcoded in the sidebar are deliberately omitted;
they reappear once the route ships.
"""
from dataclasses import dataclass


@dataclass(frozen=True)
class NavItem:
    """One row of the sidebar / one tab in the bottom bar.

    ``key`` is the value the template compares against the ``active``
    context variable to highlight the current item. ``url_name`` is a
    Django named URL — resolved via ``{% url %}`` in the template, which
    will fail loudly if a route is renamed, surfacing the breakage
    before users see it.
    """

    key: str
    label: str
    url_name: str
    icon: str


_MEMBER_NAV = [
    NavItem("dashboard", "Home", "dashboards:member", "home"),
    NavItem("menu", "Menu", "dashboards:weekly_menu", "menu"),
    NavItem("profile", "Profile", "dashboards:member_profile", "profile"),
    NavItem("help", "Help", "dashboards:member_help", "help"),
]

_CAREGIVER_NAV = [
    NavItem("dashboard", "Members", "dashboards:caregiver", "home"),
    NavItem("donate", "Donate", "donations:donate", "heart"),
]

_DONOR_NAV = [
    NavItem("history", "My donations", "dashboards:donor_history", "history"),
    NavItem("donate", "Donate", "donations:donate", "heart"),
]

_ADMIN_NAV = [
    NavItem("home", "Home", "dashboards:admin_home", "home"),
    NavItem("applications", "Applications", "dashboards:admin_applications", "users"),
    NavItem("kitchens", "Kitchens", "dashboards:admin_kitchens", "kitchen"),
    NavItem("planner", "Planner", "planning:planner", "menu"),
    NavItem("today", "Today", "delivery:admin_today", "truck"),
    NavItem("donations", "Donations", "dashboards_admin_campaigns:index", "history"),
    NavItem("audit", "Audit", "dashboards:audit_viewer", "shield"),
    NavItem("settings", "Settings", "site_config:edit", "shield"),
    NavItem("profile", "Profile", "dashboards:admin_profile", "profile"),
]

_VOLUNTEER_NAV = [
    NavItem("today", "Today", "delivery:volunteer_today", "truck"),
    NavItem("availability", "When", "volunteers:availability", "history"),
]

_KITCHEN_STAFF_NAV = [
    NavItem("receive", "Receive", "kitchens:stock_receive", "kitchen"),
    NavItem("safety", "Safety", "food_safety:safety-check", "shield"),
]

NAV_ITEMS_BY_ROLE: dict[str, list[NavItem]] = {
    "member": _MEMBER_NAV,
    "caregiver": _CAREGIVER_NAV,
    "donor": _DONOR_NAV,
    "admin": _ADMIN_NAV,
    "volunteer": _VOLUNTEER_NAV,
    "kitchen_staff": _KITCHEN_STAFF_NAV,
}


def get_nav_items(user) -> list[NavItem]:
    """Return the nav items for ``user``'s role.

    Anonymous users and users with an unknown role get an empty list so
    the sidebar/bottom-nav render to nothing — the surrounding chrome
    handles that case (no nav block at all rather than an empty box).
    Partner-affiliated members are routed to the partner outcomes page
    by ``member_dashboard_view``; they reuse the member nav while there.
    """
    if not getattr(user, "is_authenticated", False):
        return []
    role = getattr(user, "role", None)
    return list(NAV_ITEMS_BY_ROLE.get(role, []))
