"""Admin CRUD page for the singleton ``OrgSettings`` row."""
from __future__ import annotations

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.shortcuts import redirect, render

from apps.core.decorators import role_required
from apps.site_config.forms import OrgSettingsForm
from apps.site_config.models import OrgSettings


@login_required
@role_required("admin")
def org_settings_edit(request):
    """``/admin/settings/`` — GET renders the form, POST saves it.

    Single endpoint by design: there's only one row, so there's no
    list / create / delete to model. Edit is the only meaningful
    operation.
    """
    org = OrgSettings.objects.current()
    if request.method == "POST":
        form = OrgSettingsForm(request.POST, request.FILES, instance=org)
        if form.is_valid():
            form.save()
            messages.success(request, "Organisation settings saved.")
            return redirect("site_config:edit")
    else:
        form = OrgSettingsForm(instance=org)
    return render(
        request,
        "site_config/edit.html",
        {
            "form": form,
            "org": org,
            "active": "settings",
            "page_title": "Organisation settings",
        },
    )
