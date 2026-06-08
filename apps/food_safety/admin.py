from django.contrib import admin

from apps.food_safety.models import FoodSafetyCheck


@admin.register(FoodSafetyCheck)
class FoodSafetyCheckAdmin(admin.ModelAdmin):
    list_display = ("id", "kitchen", "check_type", "result",
                    "temperature_celsius", "checked_at", "checked_by")
    list_filter = ("kitchen", "result", "check_type")
    search_fields = ("notes",)
    date_hierarchy = "checked_at"
    autocomplete_fields = ("kitchen", "checked_by")
    list_select_related = ("kitchen", "checked_by")
