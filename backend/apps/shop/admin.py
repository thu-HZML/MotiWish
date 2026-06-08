from django.contrib import admin
from apps.shop.models import UserActiveEffect
from apps.shop.models import WishItem, RedemptionRecord, UserInventory


class SystemOrUserFilter(admin.SimpleListFilter):
    title = "商品归属"
    parameter_name = "scope"

    def lookups(self, request, model_admin):
        return (
            ("system", "系统公共商品"),
            ("user", "用户自定义商品"),
        )

    def queryset(self, request, queryset):
        if self.value() == "system":
            return queryset.filter(owner__isnull=True)
        if self.value() == "user":
            return queryset.filter(owner__isnull=False)
        return queryset


@admin.register(WishItem)
class WishItemAdmin(admin.ModelAdmin):
    list_display = (
        "id", 
        "title", 
        "category", 
        "price_tier", 
        "price_secondary", 
        "is_enabled", 
        "owner_display"
    )
    list_filter = (SystemOrUserFilter, "category", "price_tier", "is_enabled")
    search_fields = ("title", "catalog_key", "owner__username")
    ordering = ("owner", "-created_at")

    @admin.display(description="归属范围")
    def owner_display(self, obj):
        if obj.owner is None:
            return "🖥️ 系统公共"
        return f"👤 {obj.owner.username}"


@admin.register(RedemptionRecord)
class RedemptionRecordAdmin(admin.ModelAdmin):
    list_display = ("id", "owner", "item", "cost_secondary", "status", "created_at")
    list_filter = ("status", "created_at")
    search_fields = ("owner__username", "item__title", "note")


@admin.register(UserInventory)
class UserInventoryAdmin(admin.ModelAdmin):
    list_display = ("id", "owner", "item", "quantity", "updated_at")
    search_fields = ("owner__username", "item__title")

@admin.register(UserActiveEffect)
class UserActiveEffectAdmin(admin.ModelAdmin):
    list_display = ("id", "owner", "effect_type", "starts_at", "expires_at", "is_currently_active")
    list_filter = ("effect_type", "starts_at", "expires_at")
    search_fields = ("owner__username", "effect_type")

    @admin.display(boolean=True, description="当前是否生效")
    def is_currently_active(self, obj):
        return obj.is_active()