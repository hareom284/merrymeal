from django.contrib.auth.decorators import login_required
from django.shortcuts import render

from apps.dashboards.views.caregiver import caregiver_list_view


@login_required
def member_dashboard_view(request):
    """Member home — 'what's coming today + this week' overview.

    Phase 0: all data is mocked. Phase 3 (planning) wires `today_meal` +
    `week_menu` to MealPlan; Phase 4 (delivery) wires `delivery`.

    Role router: when a caregiver hits `/dashboard/`, defer to the
    caregiver multi-member view (Story 3.8) instead of rendering a
    member-specific template they have no use for.
    """
    if getattr(request.user, "role", None) == "caregiver":
        return caregiver_list_view(request)
    context = {
        "page_title": "Dashboard",
        "today_date_label": "Tuesday, 14 October",
        "hero": {
            "greeting_name": request.user.full_name.split()[0],
            "eta_text": "Your warm meal arrives in about 32 minutes.",
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
        "today_meal": {
            "name": "Herb-roasted chicken",
            "description": "Steamed asparagus, quinoa. Low-sodium for diabetic plan.",
            "badges": [
                {"label": "Diabetic", "tone": "green"},
                {"label": "Soft food", "tone": "neutral"},
                {"label": "410 kcal", "tone": "outline"},
            ],
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
