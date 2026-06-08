from django.shortcuts import render

from apps.core.decorators import role_required
from apps.dashboards.services.kitchen_summary import get_summary
from apps.kitchens.models import Kitchen


@role_required("admin")
def admin_kitchens(request):
    kitchens = list(Kitchen.objects.all().order_by("name"))
    cards = [get_summary(k) for k in kitchens]
    return render(
        request,
        "dashboards/admin/kitchens.html",
        {"cards": cards, "has_kitchens": bool(kitchens)},
    )
