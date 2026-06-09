"""Standalone weekly menu page (Story 12.5)."""
from django.contrib.auth.decorators import login_required
from django.shortcuts import render

from apps.dashboards.services.weekly_menu import build_weekly_menu_context


@login_required
def weekly_menu_view(request):
    context = {"active": "menu", "page_title": "This week's menu"}
    context.update(build_weekly_menu_context(request.user))
    return render(request, "dashboards/weekly_menu.html", context)
