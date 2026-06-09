"""Template context processors registered in ``config/settings/base.py``."""
from apps.dashboards.services.navigation import get_nav_items


def navigation(request):
    """Inject ``nav_items`` into every template so the app shell can
    render the sidebar / bottom-nav without each view passing it through.

    Returns an empty list for anonymous users — templates already gate
    the nav on ``request.user.is_authenticated`` for the profile section,
    so an empty list naturally hides the menu.
    """
    return {"nav_items": get_nav_items(request.user)}
