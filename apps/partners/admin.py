from django.contrib import admin

from .models import Partner


@admin.register(Partner)
class PartnerAdmin(admin.ModelAdmin):
    list_display = ("legal_name", "type", "created_at", "updated_at")
    list_filter = ("type",)
    search_fields = ("legal_name",)
    ordering = ("legal_name",)
