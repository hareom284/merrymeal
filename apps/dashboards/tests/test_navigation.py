"""Tests for the per-role navigation service + context processor.

The sidebar and mobile bottom nav both render from ``nav_items``
injected by ``apps.dashboards.context_processors.navigation``. These
tests pin two contracts:

1. Each role gets the expected menu items, and every URL name resolves
   (we don't ship dead ``href="#"`` links in production).
2. The member dashboard renders the mobile bottom nav element so a
   member on a phone always has navigation.
"""
import re

import pytest
from django.contrib.auth.models import AnonymousUser
from django.template.loader import render_to_string
from django.urls import NoReverseMatch, reverse

from apps.accounts.tests.factories import UserFactory
from apps.dashboards.services.navigation import (
    NAV_ITEMS_BY_ROLE,
    get_nav_items,
)


def test_anonymous_user_gets_no_nav_items():
    assert get_nav_items(AnonymousUser()) == []


@pytest.mark.django_db
def test_member_nav_has_dashboard_and_donate():
    user = UserFactory(role="member")
    keys = [item.key for item in get_nav_items(user)]
    assert keys == ["dashboard", "donate"]


@pytest.mark.django_db
def test_unknown_role_gets_no_nav_items():
    user = UserFactory(role="member")
    user.role = "ghost"
    assert get_nav_items(user) == []


@pytest.mark.django_db
def test_every_nav_url_name_resolves():
    """If a route is renamed, the menu must break loudly (here) rather
    than silently in production. ``reverse()`` raises NoReverseMatch
    for any url_name that no longer exists."""
    for role, items in NAV_ITEMS_BY_ROLE.items():
        for item in items:
            try:
                reverse(item.url_name)
            except NoReverseMatch as exc:  # pragma: no cover - assertion message
                pytest.fail(
                    f"NavItem for role={role!r} key={item.key!r} "
                    f"points to unknown url_name={item.url_name!r}: {exc}"
                )


@pytest.mark.django_db
def test_member_dashboard_renders_bottom_nav(client):
    """Mobile bottom nav must be present in the rendered HTML so
    members on a phone aren't stuck without navigation. We assert on
    the ``aria-label="Primary"`` marker — that's the bottom_nav <nav>
    element, distinct from any sidebar markup."""
    user = UserFactory(role="member")
    client.force_login(user)
    response = client.get("/dashboard/")
    assert response.status_code == 200
    assert b'aria-label="Primary"' in response.content
    # Confirm at least one nav item link is present (Dashboard).
    assert b"/dashboard/" in response.content


@pytest.mark.django_db
def test_no_dead_href_hash_in_nav_partials():
    """Regression: the previous hardcoded sidebar had four ``href="#"``
    placeholder links. None of them should ship now that nav is
    config-driven and only real routes appear. We render the two nav
    partials in isolation so this test stays focused on the menu and
    isn't accidentally tripped by dead links elsewhere in the page."""
    member = UserFactory.build(role="member")
    context = {
        "request": _RequestStub(member),
        "nav_items": get_nav_items(member),
        "active": "dashboard",
    }
    sidebar = render_to_string("_partials/sidebar.html", context)
    bottom_nav = render_to_string("_partials/bottom_nav.html", context)
    assert 'href="#"' not in sidebar
    assert 'href="#"' not in bottom_nav


@pytest.mark.django_db
def test_member_dashboard_has_no_unrendered_template_tags(client):
    """Catches the broken multi-line ``{# ... #}`` comment bug: Django's
    inline-comment syntax is single-line only, so a comment that wraps
    across lines renders as raw text into the HTML. The mobile dashboard
    must not leak any ``{# ... #}`` or ``{% ... %}`` markers."""
    user = UserFactory(role="member")
    client.force_login(user)
    response = client.get("/dashboard/")
    body = response.content.decode()
    assert "{#" not in body
    assert "{%" not in body
    assert not re.search(r"\{%\s*comment\s*%\}", body)


class _RequestStub:
    """Minimal stand-in for ``HttpRequest`` so the nav partials render
    in isolation. They only touch ``request.user`` (auth check + name)."""

    def __init__(self, user):
        self.user = user
