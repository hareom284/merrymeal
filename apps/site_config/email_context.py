"""Helper for rendering transactional emails with the org context.

Django's template context processors only fire on ``render(request, …)``
— they're skipped by ``render_to_string`` used in the email pipeline.
Every email base template references ``{{ org }}`` for the header and
footer, so without this helper each call site has to remember to pass
``"org": OrgSettings.objects.current()`` into the context dict.

Use ``render_email`` instead of ``render_to_string`` for any template
that extends ``emails/_base.html`` and the org will be there
automatically.
"""
from __future__ import annotations

from typing import Any

from django.template.loader import render_to_string


def render_email(template_name: str, context: dict[str, Any] | None = None) -> str:
    """Render ``template_name`` with the org singleton merged in.

    ``context`` overrides win — a caller that wants to mock the org for
    a specific email can still pass ``"org": some_other_value``.
    """
    from apps.site_config.models import OrgSettings

    ctx: dict[str, Any] = {}
    try:
        ctx["org"] = OrgSettings.objects.current()
    except Exception:
        # Cold-boot path (table doesn't exist yet) — the email base
        # has ``|default:"MerryMeal"`` fallbacks so a missing org is
        # cosmetic, not fatal.
        ctx["org"] = None
    if context:
        ctx.update(context)
    return render_to_string(template_name, ctx)
