"""View entry points for the donations app.

Re-exports the per-feature view callables so URL configs can
``from apps.donations.views import impact_view`` without reaching into
private modules.
"""
from apps.donations.views.impact import impact_view

__all__ = ["impact_view"]
