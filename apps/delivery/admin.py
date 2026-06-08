from django.contrib import admin

from apps.delivery.models import Route


@admin.register(Route)
class RouteAdmin(admin.ModelAdmin):
    list_display = ("id", "volunteer", "route_date", "status", "created_at")
    list_filter = ("status", "route_date", "volunteer")
    date_hierarchy = "route_date"
    search_fields = ("volunteer__email", "volunteer__full_name")
    autocomplete_fields = ("volunteer",)
