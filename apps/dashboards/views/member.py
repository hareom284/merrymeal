from django.contrib.auth.decorators import login_required
from django.shortcuts import redirect, render
from django.utils import timezone

from apps.dashboards.services.member_today import get_today_card
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
    """Member home.

    Story 3.4 wires the "today's meal" card to real ``MealPlan`` data via
    ``get_today_card``. The hero ETA, the 3-stage delivery progress, the
    week-menu strip and the rate-yesterday card are still mock — those
    belong to Epic 04 (delivery) and Story 3.6 (week menu) and will be
    swapped out as those services land.
    """
    role = getattr(request.user, "role", None)
    if role == "caregiver":
        return caregiver_list_view(request)
    if role in ROLE_HOME_URLS:
        return redirect(ROLE_HOME_URLS[role])
    if request.user.partner_id:
        return redirect("dashboards:partner_outcomes")

    today = timezone.localdate()
    full_name = (request.user.full_name or request.user.email or "there").strip()
    greeting_name = full_name.split()[0] if full_name else "there"
    card = get_today_card(request.user)
    context = {
        "page_title": "Dashboard",
        "today_date_label": today.strftime("%A, %d %B"),
        "card": card,
        "hero": {
            "greeting_name": greeting_name,
            "eta_text": (
                "Your warm meal arrives in about 32 minutes."
                if card["has_meal"]
                else "No meal scheduled for today."
            ),
            "eta_time": "12:32",
            "eta_period": "PM",
        },
        "delivery": {
            "status_label": "On the way",
            "stages": [
                {"name": "Cooked", "subtitle": "10:30 AM", "state": "done"},
                {"name": "On the way", "subtitle": "Sarah · ~32 min", "state": "active"},
                {"name": "Delivered", "subtitle": "Expected 12-1 PM", "state": "pending"},
            ],
            "volunteer": {
                "initials": "SM",
                "name": "Sarah M.",
                "subtitle": "Your volunteer · 12 stops on her route",
            },
        },
        "week_menu": [
            {"day": "MON", "meal": "Lentil stew", "state": "done"},
            {"day": "TUE", "meal": "Herb chicken", "state": "today"},
            {"day": "WED", "meal": "Fish pie", "state": "upcoming"},
            {"day": "THU", "meal": "Pasta primave…", "state": "upcoming"},
            {"day": "FRI", "meal": "Roast veg", "state": "upcoming"},
        ],
        "feedback_prompt": {
            "meal": "Baked salmon",
            "question": "Baked salmon — how was it?",
        },
    }
    return render(request, "dashboards/member.html", context)
