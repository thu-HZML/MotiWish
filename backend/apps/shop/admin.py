from django.contrib import admin

from apps.shop.models import RedemptionRecord, WishItem


@admin.register(WishItem)
class WishItemAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "catalog_key",
        "title",
        "owner",
        "category",
        "item_kind",
        "rarity",
        "price_tier",
        "price_secondary",
        "inventory",
        "source",
        "is_enabled",
        "auto_refund_on_reject",
    )
    list_filter = ("category", "item_kind", "rarity", "price_tier", "source", "is_enabled", "auto_refund_on_reject")


@admin.register(RedemptionRecord)
class RedemptionRecordAdmin(admin.ModelAdmin):
    list_display = ("id", "owner", "item", "cost_secondary", "status", "fulfilled_at", "rejected_at", "created_at")
    list_filter = ("status",)
