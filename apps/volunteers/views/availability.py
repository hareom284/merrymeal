from django.contrib.auth.decorators import login_required
from django.http import HttpResponseBadRequest
from django.shortcuts import render
from django.views.decorators.http import require_GET, require_POST

from apps.core.decorators import role_required
from apps.volunteers.models import Availability
from apps.volunteers.services import toggle_slot


def _cell_context(volunteer, day: str, phrase: str, active: bool) -> dict:
    return {"day": day, "phrase": phrase, "active": active}


@login_required
@role_required("volunteer")
@require_GET
def availability_view(request):
    active = {
        (a.day_of_week, a.day_phrase)
        for a in Availability.objects.filter(volunteer=request.user)
    }
    grid = [
        {
            "day": day,
            "day_label": label,
            "cells": [
                _cell_context(request.user, day, phrase, (day, phrase) in active)
                for phrase, _ in Availability.DAY_PHRASE_CHOICES
            ],
        }
        for day, label in Availability.DAY_OF_WEEK_CHOICES
    ]
    return render(request, "volunteers/availability.html", {"grid": grid})


@login_required
@role_required("volunteer")
@require_POST
def toggle_view(request):
    day = request.POST.get("day", "")
    phrase = request.POST.get("phrase", "")
    try:
        active = toggle_slot(request.user, day, phrase)
    except ValueError as exc:
        return HttpResponseBadRequest(str(exc))
    return render(
        request,
        "volunteers/_slot_cell.html",
        _cell_context(request.user, day, phrase, active),
    )
