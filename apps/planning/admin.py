from django.contrib import admin

from apps.planning.models import MealPlan


@admin.register(MealPlan)
class MealPlanAdmin(admin.ModelAdmin):
    list_display = (
        "service_date", "day_of_week", "kitchen",
        "meal", "meal_type", "planned_quantity",
    )
    list_filter = ("kitchen", "meal_type", "day_of_week")
    date_hierarchy = "service_date"
    search_fields = ("meal__name", "kitchen__name")
    autocomplete_fields = ("meal", "kitchen", "published_by")
    ordering = ("-service_date", "kitchen__name")
