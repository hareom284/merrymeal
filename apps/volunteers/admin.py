from django.contrib import admin

from apps.volunteers.models import Availability


@admin.register(Availability)
class AvailabilityAdmin(admin.ModelAdmin):
    list_display = ("id", "volunteer", "day_of_week", "day_phrase")
    list_filter = ("day_of_week", "day_phrase")
    search_fields = ("volunteer__email", "volunteer__full_name")
    autocomplete_fields = ("volunteer",)
