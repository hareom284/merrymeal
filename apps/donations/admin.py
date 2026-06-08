from django.contrib import admin
from django.utils.html import format_html

from apps.donations.models import Campaign, Donation
from apps.donations.services.campaigns import raised_cents_for
from apps.donations.templatetags.donation_extras import dollars


@admin.register(Campaign)
class CampaignAdmin(admin.ModelAdmin):
    """Admin for fundraising campaigns.

    Display logic (progress bar, dollar formatting) lives here rather than
    on the model — per MerryMeal conventions the model is schema-only.
    Computation of ``raised_cents`` is delegated to
    ``apps.donations.services.campaigns.raised_cents_for`` so the same
    query is reused by the donate page and weekly digest.
    """

    list_display = (
        "name",
        "is_active",
        "goal_display",
        "raised_display",
        "progress_bar",
    )
    list_filter = ("is_active",)
    search_fields = ("name", "slug")
    prepopulated_fields = {"slug": ("name",)}
    readonly_fields = ("created_at",)

    @admin.display(description="Goal")
    def goal_display(self, obj):
        return dollars(obj.goal_cents)

    @admin.display(description="Raised")
    def raised_display(self, obj):
        return dollars(raised_cents_for(obj))

    @admin.display(description="Progress")
    def progress_bar(self, obj):
        raised = raised_cents_for(obj)
        pct = 0 if not obj.goal_cents else min(100, int(raised * 100 / obj.goal_cents))
        return format_html(
            '<div class="progress" style="background:#eee;width:160px;height:10px;'
            'border-radius:4px;display:inline-block;vertical-align:middle;">'
            '<div style="width:{}%;background:#0f766e;height:10px;border-radius:4px;">'
            "</div></div> <span>{}%</span>",
            pct,
            pct,
        )


@admin.register(Donation)
class DonationAdmin(admin.ModelAdmin):
    """Admin for individual donation pledges.

    Filters by ``campaign`` / ``status`` / ``payment_type`` / ``is_recurring``
    cover the day-to-day reconciliation queries finance run (which
    Stripe charges failed, which subscriptions are still active).
    Default sort is ``-amount_cents`` because the largest gifts deserve
    a thank-you email first.
    """

    list_display = (
        "created_at",
        "donor_email",
        "campaign",
        "amount_display",
        "status",
        "payment_type",
        "transaction_id",
    )
    list_filter = ("campaign", "status", "payment_type", "is_recurring")
    search_fields = ("donor_email", "transaction_id", "receipt_number")
    ordering = ("-amount_cents",)
    readonly_fields = ("created_at", "updated_at")
    list_select_related = ("campaign",)

    @admin.display(description="Amount", ordering="amount_cents")
    def amount_display(self, obj):
        return dollars(obj.amount_cents)
