from django.contrib import admin

from apps.shop.models import RedemptionRecord, WishItem


@admin.register(WishItem)
class WishItemAdmin(admin.ModelAdmin):
    list_display = ("id", "title", "owner", "price_secondary", "inventory", "source", "is_enabled")
    list_filter = ("source", "is_enabled")


@admin.register(RedemptionRecord)
class RedemptionRecordAdmin(admin.ModelAdmin):
    list_display = ("id", "owner", "item", "cost_secondary", "status", "created_at")
    list_filter = ("status",)
