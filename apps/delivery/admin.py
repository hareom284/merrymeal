from django.contrib import admin

from apps.delivery.models import Delivery, Route


@admin.register(Route)
class RouteAdmin(admin.ModelAdmin):
    list_display = ("id", "volunteer", "route_date", "status", "created_at")
    list_filter = ("status", "route_date", "volunteer")
    date_hierarchy = "route_date"
    search_fields = ("volunteer__email", "volunteer__full_name")
    autocomplete_fields = ("volunteer",)


@admin.register(Delivery)
class DeliveryAdmin(admin.ModelAdmin):
    list_display = (
        "id", "member", "scheduled_date", "status", "meal_type",
        "volunteer", "route",
    )
    list_filter = ("status", "scheduled_date", "meal_type")
    date_hierarchy = "scheduled_date"
    search_fields = ("member__email", "member__full_name")
    # `member_address` is not in autocomplete_fields because `accounts.Address`
    # is only registered as an admin inline (no standalone ModelAdmin), so
    # adding it here trips admin.E039. Use raw_id_fields as a fallback.
    autocomplete_fields = ("route", "meal_plan", "volunteer", "member")
    raw_id_fields = ("member_address",)
