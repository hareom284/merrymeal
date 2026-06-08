from datetime import date, timedelta
from decimal import Decimal

from django.contrib import admin

from apps.kitchens.models import Ingredient, IngredientBatch, Kitchen


@admin.register(Kitchen)
class KitchenAdmin(admin.ModelAdmin):
    list_display = ("name", "is_outsourced", "latitude", "longitude", "service_radius_km")
    list_filter = ("is_outsourced",)
    search_fields = ("name",)
    ordering = ("name",)


@admin.register(Ingredient)
class IngredientAdmin(admin.ModelAdmin):
    list_display = ("name", "unit")
    list_filter = ("unit",)
    search_fields = ("name",)
    ordering = ("name",)


class ExpiringSoonFilter(admin.SimpleListFilter):
    title = "Expiring soon"
    parameter_name = "expiring"

    def lookups(self, request, model_admin):
        return [("soon", "Expiring in ≤ 3 days")]

    def queryset(self, request, queryset):
        if self.value() == "soon":
            cutoff = date.today() + timedelta(days=3)
            return queryset.filter(
                expiration_date__lte=cutoff, quantity__gt=Decimal("0")
            )
        return queryset


@admin.register(IngredientBatch)
class IngredientBatchAdmin(admin.ModelAdmin):
    list_display = (
        "ingredient",
        "kitchen",
        "quantity",
        "received_at",
        "expiration_date",
        "days_until_expiry",
    )
    list_filter = (ExpiringSoonFilter, "kitchen", "expiration_date")
    search_fields = ("lot_number", "ingredient__name")
    autocomplete_fields = ("ingredient", "kitchen")
    ordering = ("expiration_date",)
    date_hierarchy = "expiration_date"

    @admin.display(description="Days to expiry", ordering="expiration_date")
    def days_until_expiry(self, obj: IngredientBatch) -> int:
        return (obj.expiration_date - date.today()).days
