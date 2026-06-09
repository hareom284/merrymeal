from django.contrib.auth.decorators import login_required
from django.shortcuts import redirect, render

from apps.dashboards.services.member_dashboard import build_member_dashboard_context
from apps.dashboards.views.caregiver import caregiver_list_view

# Every non-member role has its own home elsewhere. ``/dashboard/`` is
# the single post-login landing URL (see ``apps.dashboards.views.landing``),
# so this view doubles as the role router that fans users out to the
# correct screen. ``caregiver`` is handled inline below because it
# renders directly without changing URL (Story 3.8). ``member`` (and any
# partner-affiliated member) falls through to the member template.
ROLE_HOME_URLS = {
    "admin": "dashboards:admin_home",
    "volunteer": "delivery:volunteer_today",
    "donor": "dashboards:donor_history",
    "kitchen_staff": "kitchens:stock_receive",
}


@login_required
def member_dashboard_view(request):
    """Member home — every section pulled live from the DB.

    Composition lives in ``build_member_dashboard_context``. Sections
    with no underlying data return ``None`` (delivery, feedback prompt)
    or a placeholder strip (week menu) so the template hides them
    instead of fabricating a "Sarah · 32 min" experience for a member
    who has no delivery on the way.
    """
    role = getattr(request.user, "role", None)
    if role == "caregiver":
        return caregiver_list_view(request)
    if role in ROLE_HOME_URLS:
        return redirect(ROLE_HOME_URLS[role])
    if request.user.partner_id:
        return redirect("dashboards:partner_outcomes")

    context = {"page_title": "Dashboard"}
    context.update(build_member_dashboard_context(request.user))
    return render(request, "dashboards/member.html", context)
