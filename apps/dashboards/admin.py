"""Defence-in-depth: lock down ``django-auditlog``'s LogEntry admin.

Even though the project does not currently mount Django's built-in
admin on a public URL, ``django-auditlog`` ships its own ``ModelAdmin``
that exposes add / change / delete actions to any superuser who can
reach ``/admin/``. Story 6.6 forbids that — the audit log is
read-only **everywhere**, including the Django admin — so we re-
register ``LogEntry`` with all three mutation permissions denied.
"""
from auditlog.models import LogEntry
from django.contrib import admin


class ReadOnlyLogEntryAdmin(admin.ModelAdmin):
    """Disallow add / change / delete on ``LogEntry`` for every user."""

    # We deliberately do NOT subclass ``auditlog.admin.LogEntryAdmin``:
    # its permission overrides inspect ``request.resolver_match`` and
    # would crash if we ever called them with ``request=None`` (as
    # happens in unit tests). A bare ``ModelAdmin`` keeps the list /
    # detail views available for inspection while making the mutation
    # affordances impossible.

    def has_add_permission(self, request, obj=None):
        return False

    def has_change_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return False


try:
    admin.site.unregister(LogEntry)
except admin.sites.NotRegistered:
    pass
admin.site.register(LogEntry, ReadOnlyLogEntryAdmin)
