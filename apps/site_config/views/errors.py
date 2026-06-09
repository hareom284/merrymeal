"""Custom 404 / 500 error pages.

Django wires these via ``handler404`` / ``handler500`` in
``config/urls.py``. Each view returns a minimal HTML page that
extends ``base.html`` so the brand chrome stays consistent and the
``{{ org }}`` context processor still drops in the right phone
number, even on an error screen.
"""
from __future__ import annotations

from django.shortcuts import render
from django.template import loader


def not_found_view(request, exception=None):
    return render(request, "errors/404.html", status=404)


def server_error_view(request):
    """500 handler — runs outside the normal context-processor chain
    when the error is severe enough that middleware fails. We
    therefore render the template directly (no ``render()`` shortcut
    that calls back into Django's response middleware) and pass the
    minimal context manually so a broken context processor can't
    cause a recursive 500."""
    template = loader.get_template("errors/500.html")
    return type(template.render(request=request))(
        template.render(request=request),
        content_type="text/html",
        status=500,
    )
