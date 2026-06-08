"""Smoke tests for ``CampaignAdmin``.

The project intentionally does not mount Django's built-in ``admin`` URL
namespace (see ``config/urls.py``) — operational UIs are custom views.
So we exercise the admin the same way other apps' tests do
(see ``apps/kitchens/tests/test_kitchens.py``): via the registry plus
direct invocation of the display methods. That still covers what Story
5.1 asks for: registration, column wiring, prepopulated slug, and the
progress-bar markup.
"""

import pytest
from django.contrib.admin.sites import site

from apps.donations.admin import CampaignAdmin
from apps.donations.models import Campaign
from apps.donations.tests.factories import CampaignFactory


class TestCampaignAdminRegistration:
    def test_campaign_is_registered(self):
        assert site.is_registered(Campaign)

    def test_list_display_columns(self):
        admin = site._registry[Campaign]
        assert "name" in admin.list_display
        assert "is_active" in admin.list_display
        assert "goal_display" in admin.list_display
        assert "raised_display" in admin.list_display
        assert "progress_bar" in admin.list_display

    def test_slug_is_prepopulated_from_name(self):
        admin = site._registry[Campaign]
        assert admin.prepopulated_fields == {"slug": ("name",)}


@pytest.mark.django_db
class TestCampaignAdminDisplays:
    def test_goal_display_renders_dollars(self):
        c = CampaignFactory(goal_cents=10_000_00)
        admin = CampaignAdmin(Campaign, site)
        assert admin.goal_display(c) == "$10,000.00"

    def test_progress_bar_renders_zero_percent_when_no_donations(self):
        c = CampaignFactory(goal_cents=10_000_00)
        admin = CampaignAdmin(Campaign, site)
        html = admin.progress_bar(c)
        assert "progress" in html.lower()
        assert "0%" in html

    def test_progress_bar_handles_zero_goal(self):
        # A campaign with goal_cents=0 must not divide by zero — the bar
        # renders at 0 % rather than blowing up.
        c = CampaignFactory(goal_cents=0)
        admin = CampaignAdmin(Campaign, site)
        html = admin.progress_bar(c)
        assert "0%" in html

    def test_raised_display_is_zero_until_completed_donations_exist(self):
        c = CampaignFactory(goal_cents=10_000_00)
        admin = CampaignAdmin(Campaign, site)
        assert admin.raised_display(c) == "$0.00"
