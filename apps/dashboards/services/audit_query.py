"""Audit log read-only queries (Story 6.6).

This module **never** writes to ``auditlog.LogEntry``. The viewer it
backs is for inspection only — even helper functions return querysets,
not instances. Callers should treat the result as immutable.
"""
from __future__ import annotations

from datetime import date

from auditlog.models import LogEntry
from django.contrib.contenttypes.models import ContentType
from django.db.models import QuerySet

# URL value → ``LogEntry.Action`` integer. Centralised here so the view
# and any future API surface agree on the wire vocabulary.
ACTION_CHOICES = {
    "create": LogEntry.Action.CREATE,
    "update": LogEntry.Action.UPDATE,
    "delete": LogEntry.Action.DELETE,
    "access": LogEntry.Action.ACCESS,
}


def filtered(
    *,
    email: str | None = None,
    object_type: str | None = None,
    date_from: date | None = None,
    date_to: date | None = None,
    action: str | None = None,
) -> QuerySet[LogEntry]:
    """Return an ordered ``LogEntry`` queryset matching the given filters.

    All filters are optional. Missing or empty filters are treated as
    "no constraint". An ``object_type`` that does not resolve to a
    known ``ContentType`` returns an empty queryset (so a typo in the
    query string is a no-op, not a 500). ``select_related`` is applied
    so the per-row render does not fire N+1 queries.
    """
    qs = (
        LogEntry.objects.select_related("actor", "content_type")
        .order_by("-timestamp")
    )
    if email:
        qs = qs.filter(actor__email__icontains=email)
    if object_type:
        app_label, _, model = object_type.partition(".")
        try:
            ct = ContentType.objects.get(app_label=app_label, model=model)
        except ContentType.DoesNotExist:
            return qs.none()
        qs = qs.filter(content_type=ct)
    if date_from:
        qs = qs.filter(timestamp__date__gte=date_from)
    if date_to:
        qs = qs.filter(timestamp__date__lte=date_to)
    if action and action in ACTION_CHOICES:
        qs = qs.filter(action=ACTION_CHOICES[action])
    return qs
