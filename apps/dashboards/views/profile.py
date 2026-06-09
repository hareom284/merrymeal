"""My profile page (Story 12.4) — read-only for v1."""
from django.contrib.auth.decorators import login_required
from django.shortcuts import render

from apps.dashboards.services.profile import build_member_profile_context


@login_required
def member_profile_view(request):
    context = {"active": "profile", "page_title": "My profile"}
    context.update(build_member_profile_context(request.user))
    return render(request, "dashboards/profile.html", context)
