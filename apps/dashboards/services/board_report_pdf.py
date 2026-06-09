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

import contextlib
import io
import logging
import os
import sys
import warnings

from django.template.loader import render_to_string

from apps.dashboards.services.board_report import BoardReport

logger = logging.getLogger(__name__)


@contextlib.contextmanager
def _silence_all_io():
    """Mute Python-level AND OS-level stdout/stderr.

    WeasyPrint prints a multi-line install-help banner when libpango /
    libcairo cannot be dlopened on import. Different versions emit it
    through different paths (``sys.stderr.write``, ``print(...)`` to
    stdout, or directly via the C/cffi side to fd 1/2), so we silence
    every channel: rebind ``sys.stdout`` + ``sys.stderr`` to in-memory
    buffers AND dup fds 1+2 to ``/dev/null`` for the duration of the
    import, flush before restoring so nothing leaks out the back.
    """
    devnull_fd = os.open(os.devnull, os.O_WRONLY)
    saved_stdout_fd = os.dup(1)
    saved_stderr_fd = os.dup(2)
    saved_py_stdout = sys.stdout
    saved_py_stderr = sys.stderr
    sys.stdout.flush()
    sys.stderr.flush()
    try:
        os.dup2(devnull_fd, 1)
        os.dup2(devnull_fd, 2)
        sys.stdout = io.StringIO()
        sys.stderr = io.StringIO()
        yield
    finally:
        try:
            sys.stdout.flush()
            sys.stderr.flush()
        except Exception:  # noqa: BLE001
            pass
        sys.stdout = saved_py_stdout
        sys.stderr = saved_py_stderr
        os.dup2(saved_stdout_fd, 1)
        os.dup2(saved_stderr_fd, 2)
        os.close(devnull_fd)
        os.close(saved_stdout_fd)
        os.close(saved_stderr_fd)


try:  # pragma: no cover - import-time branch is environment-dependent
    with _silence_all_io(), warnings.catch_warnings():
        warnings.simplefilter("ignore")
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
