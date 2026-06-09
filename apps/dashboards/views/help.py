"""Help & contact landing page for members (Story 12.3).

Pure presentation — no service layer needed. Quick-action links point at
the relevant existing pages (or ``mailto:`` placeholders for routes
that haven't shipped yet). When sprint 13's pause page lands, swap the
mailto for ``{% url 'dashboards:member_pause' %}``.
"""
from django.contrib.auth.decorators import login_required
from django.shortcuts import render

_FAQS = [
    {
        "q": "What time will my meal arrive?",
        "a": (
            "Most lunches arrive between 11:30am and 1:00pm. Your dashboard "
            "shows the live ETA on delivery day."
        ),
    },
    {
        "q": "How do I report an allergy?",
        "a": (
            "Call us on (555) 444-MEAL or use the 'Update dietary needs' "
            "quick action above. We'll flag every meal plan from the next "
            "kitchen run."
        ),
    },
    {
        "q": "Can I share my meal?",
        "a": (
            "MerryMeal portions are sized for one adult and are part of a "
            "subsidised program. Please don't share — if you need an extra "
            "portion for a partner or carer, contact us."
        ),
    },
    {
        "q": "Who is my care worker?",
        "a": (
            "Your linked caregiver appears on the My profile page under "
            "Emergency contact. Call or message them via that page."
        ),
    },
]


@login_required
def help_view(request):
    return render(
        request,
        "dashboards/help.html",
        {"active": "help", "faqs": _FAQS},
    )
