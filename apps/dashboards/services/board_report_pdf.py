"""Story 6.5 — PDF renderer for the board report.

WeasyPrint is the rendering engine. It pulls in native system libs
(``libpango``, ``libcairo2``) which are installed in the Debian-slim
runtime image via the Dockerfile. On a developer's macOS workstation
without ``brew install pango cairo``, the import fails with
``OSError: cannot load library 'libgobject-2.0-0'`` (or similar).

To keep the local dev experience friction-free we:

* Wrap the ``weasyprint`` import in ``try/except`` at module load so
  ``manage.py``, ``pytest`` collection, and ``ruff`` do not blow up.
* Expose a single sentinel ``WEASYPRINT_AVAILABLE`` flag callers
  inspect. ``render_pdf`` returns ``None`` (not raises) when the
  engine is unavailable so the view can fall back to the print-
  friendly HTML page with a banner pointing at ``File → Print → Save
  as PDF``.
* Defer the actual ``HTML(...).write_pdf()`` call to render-time so a
  half-installed weasyprint (import succeeds, libpango missing) still
  surfaces a clean ``None`` result rather than a 500.

In production (Docker image) WEASYPRINT_AVAILABLE is True and the PDF
branch always serves bytes.
"""
from __future__ import annotations

import logging

from django.template.loader import render_to_string

from apps.dashboards.services.board_report import BoardReport

logger = logging.getLogger(__name__)

try:  # pragma: no cover - import-time branch is environment-dependent
    import weasyprint as _weasyprint  # type: ignore[import-not-found]

    WEASYPRINT_AVAILABLE = True
except Exception as exc:  # noqa: BLE001 — both ImportError and OSError matter
    _weasyprint = None
    WEASYPRINT_AVAILABLE = False
    logger.info("weasyprint unavailable; PDF endpoint will fall back to HTML (%s)", exc)


def render_pdf(report: BoardReport) -> bytes | None:
    """Render the board report as PDF bytes, or ``None`` on failure.

    ``None`` signals the caller to fall back to the HTML print view.
    Never raises — a missing native lib at render-time is treated the
    same as a missing import.
    """
    if not WEASYPRINT_AVAILABLE or _weasyprint is None:
        return None
    try:
        html = render_to_string(
            "dashboards/admin/board_report.html",
            {"report": report, "for_pdf": True},
        )
        return _weasyprint.HTML(string=html).write_pdf()
    except Exception as exc:  # noqa: BLE001 - native lib failures vary
        logger.warning("weasyprint render failed; falling back to HTML (%s)", exc)
        return None
