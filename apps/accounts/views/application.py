from django.shortcuts import redirect, render
from django.views.decorators.http import require_http_methods

from apps.accounts.forms import (
    ApplicationAddressForm,
    ApplicationContactForm,
    ApplicationDietaryForm,
)
from apps.accounts.models import Application
from apps.accounts.services import (
    create_draft_application,
    submit_application,
    update_application_address,
)


def _load_draft_from_session(request):
    """Return the draft Application bound to this session, or None.

    Side-effect: clears the session key if the application is no longer in
    draft state (already submitted / approved / rejected).
    """
    app_id = request.session.get("application_id")
    if not app_id:
        return None
    try:
        app = Application.objects.get(id=app_id)
    except Application.DoesNotExist:
        request.session.pop("application_id", None)
        return None
    if app.status != Application.STATUS_DRAFT:
        request.session.pop("application_id", None)
        return None
    return app


@require_http_methods(["GET", "POST"])
def application_step_1(request):
    if request.method == "GET" and "application_id" not in request.session:
        request.session.pop("existing_caregiver", None)

    if request.method == "POST":
        form = ApplicationContactForm(request.POST)
        if form.is_valid():
            data = form.cleaned_data
            existing_caregiver = data.pop("existing_caregiver", False)
            app = create_draft_application(
                full_name=data["full_name"],
                email=data["email"],
                dob=data["dob"],
                phone=data.get("phone"),
                applying_for_other=data.get("applying_for_other", False),
                caregiver_full_name=data.get("caregiver_full_name"),
                caregiver_email=data.get("caregiver_email"),
                caregiver_phone=data.get("caregiver_phone"),
                relationship=data.get("relationship"),
            )
            request.session["application_id"] = app.id
            request.session["existing_caregiver"] = bool(existing_caregiver)
            return redirect("/apply/address/")
    else:
        form = ApplicationContactForm()

    return render(
        request,
        "accounts/application/step_1.html",
        {"form": form, "step": 1},
    )


@require_http_methods(["GET", "POST"])
def application_step_2(request):
    application = _load_draft_from_session(request)
    if application is None:
        return redirect("/apply/")

    if request.method == "POST":
        form = ApplicationAddressForm(request.POST)
        if form.is_valid():
            update_application_address(
                application=application,
                **form.cleaned_data,
            )
            return redirect("/apply/dietary/")
    else:
        form = ApplicationAddressForm(
            initial={
                "label": application.address_label or "Home",
                "street": application.street or "",
                "postal_code": application.postal_code or "",
                "city": application.city_id,
            }
        )

    return render(
        request,
        "accounts/application/step_2.html",
        {"form": form, "step": 2, "application": application},
    )


@require_http_methods(["GET", "POST"])
def application_step_3(request):
    application = _load_draft_from_session(request)
    if application is None:
        return redirect("/apply/")

    from apps.dietary.models import Allergy, DietPreference

    if request.method == "POST":
        form = ApplicationDietaryForm(request.POST)
        if form.is_valid():
            submit_application(
                application_id=application.id,
                dietary_ids=form.cleaned_data["dietary_ids"],
                allergy_ids=form.cleaned_data["allergy_ids"],
            )
            request.session.pop("application_id", None)
            request.session.pop("existing_caregiver", None)
            return redirect("/apply/done/")
    else:
        form = ApplicationDietaryForm(
            initial={
                "dietary_ids": application.dietary_ids or [],
                "allergy_ids": application.allergy_ids or [],
            }
        )

    return render(
        request,
        "accounts/application/step_3.html",
        {
            "form": form,
            "step": 3,
            "diet_choices": list(DietPreference.objects.order_by("name")),
            "allergy_choices": list(Allergy.objects.order_by("name")),
        },
    )


@require_http_methods(["GET"])
def application_done(request):
    return render(request, "accounts/application/done.html")
