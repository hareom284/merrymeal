"""Admin profile page (Story 12.10) — read-only for v1.

Admins don't need much: who am I (name/email/role), when did I last sign
in, what does the system know about my permissions, and a sign-out
button. Editing admin fields happens via the CLI / direct DB until a
dedicated user-management UI ships.
"""
from django.shortcuts import render

from apps.core.decorators import role_required


@role_required("admin")
def admin_profile_view(request):
    return render(
        request,
        "dashboards/admin/profile.html",
        {
            "active": "profile",
            "page_title": "My profile",
            "admin": request.user,
        },
    )
