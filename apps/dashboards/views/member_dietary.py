from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.shortcuts import redirect, render
from django.urls import reverse

from apps.core.decorators import role_required
from apps.dashboards.forms.member_dietary import MemberDietaryForm
from apps.dashboards.services.member_dietary import update_member_dietary


@login_required
@role_required("member")
def member_dietary_edit_view(request):
    if request.method == "POST":
        form = MemberDietaryForm.for_user(request.user, data=request.POST)
        if form.is_valid():
            update_member_dietary(
                user=request.user,
                diet_preference_ids=[
                    p.pk for p in form.cleaned_data["diet_preferences"]
                ],
                allergy_ids=[a.pk for a in form.cleaned_data["allergies"]],
            )
            messages.success(request, "Dietary preferences updated.")
            return redirect(reverse("dashboards:member_profile"))
    else:
        form = MemberDietaryForm.for_user(request.user)

    return render(
        request,
        "dashboards/member/dietary_form.html",
        {
            "active": "profile",
            "page_title": "Edit dietary preferences",
            "form": form,
        },
    )
