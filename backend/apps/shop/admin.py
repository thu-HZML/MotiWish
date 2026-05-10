from django import forms
from django.contrib import admin, messages
from django.db import models

from apps.shop.models import (
    RedemptionRecord,
    ShopItemCategory,
    ShopItemKind,
    UserInventory,
    WishItem,
)
from apps.shop.services import ensure_default_shop_items


class WishItemAdminForm(forms.ModelForm):
    class Meta:
        model = WishItem
        fields = "__all__"

    def clean(self):
        cleaned_data = super().clean()
        category = cleaned_data.get("category")
        item_kind = cleaned_data.get("item_kind")
        effect_payload = cleaned_data.get("effect_payload") or {}

        if category == ShopItemCategory.GROWTH_MATERIAL:
            if item_kind != ShopItemKind.EXPERIENCE_PACK:
                raise forms.ValidationError("养成材料目前只能选择 experience_pack。")
            if int(effect_payload.get("experience", 0)) <= 0:
                raise forms.ValidationError("经验材料必须在 effect_payload 中配置正数 experience。")

        if category == ShopItemCategory.UTILITY_ITEM and item_kind not in {
            ShopItemKind.DEBT_REPAYMENT_CARD,
            ShopItemKind.TASK_FAILURE_PROTECTION_CARD,
            ShopItemKind.INDULGENCE_DAY_CARD,
        }:
            raise forms.ValidationError("功能轻道具的 item_kind 不合法。")

        if category == ShopItemCategory.WISH_REWARD and item_kind != ShopItemKind.WISH:
            raise forms.ValidationError("愿望奖励的 item_kind 必须为 wish。")

        return cleaned_data


@admin.register(WishItem)
class WishItemAdmin(admin.ModelAdmin):
    form = WishItemAdminForm
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
        "is_stackable",
        "updated_at",
    )
    list_display_links = ("id", "title")
    list_editable = ("price_secondary", "inventory", "is_enabled")
    list_filter = (
        "category",
        "item_kind",
        "rarity",
        "price_tier",
        "source",
        "is_enabled",
        "is_stackable",
        "auto_refund_on_reject",
    )
    search_fields = ("title", "catalog_key", "owner__username", "owner__email")
    raw_id_fields = ("owner",)
    readonly_fields = ("created_at", "updated_at")
    actions = ("enable_items", "disable_items", "sync_default_catalog_for_selected_owners")
    save_on_top = True
    list_per_page = 50
    formfield_overrides = {
        models.JSONField: {"widget": forms.Textarea(attrs={"rows": 8, "cols": 80})},
    }
    fieldsets = (
        (
            "基础信息",
            {
                "fields": (
                    "owner",
                    "catalog_key",
                    "title",
                    "description",
                    "source",
                    "is_enabled",
                )
            },
        ),
        (
            "分类与展示",
            {
                "fields": (
                    "category",
                    "item_kind",
                    "rarity",
                    "price_tier",
                )
            },
        ),
        (
            "价格与库存",
            {
                "fields": (
                    "price_secondary",
                    "inventory",
                    "is_stackable",
                    "auto_refund_on_reject",
                )
            },
        ),
        (
            "效果配置",
            {
                "description": (
                    "经验材料示例：{\"experience\": 160}；"
                    "还债卡示例：{\"effect\": \"debt_reset\"}。"
                ),
                "fields": ("effect_payload", "ai_pricing"),
            },
        ),
        ("时间", {"fields": ("created_at", "updated_at")}),
    )

    @admin.action(description="上架所选商品")
    def enable_items(self, request, queryset):
        updated = queryset.update(is_enabled=True)
        self.message_user(request, f"已上架 {updated} 个商品。", messages.SUCCESS)

    @admin.action(description="下架所选商品")
    def disable_items(self, request, queryset):
        updated = queryset.update(is_enabled=False)
        self.message_user(request, f"已下架 {updated} 个商品。", messages.SUCCESS)

    @admin.action(description="为所选商品的所属用户补齐默认商品")
    def sync_default_catalog_for_selected_owners(self, request, queryset):
        owners = {item.owner for item in queryset.select_related("owner")}
        created_count = 0
        for owner in owners:
            created_count += len(ensure_default_shop_items(user=owner))
        self.message_user(request, f"已为 {len(owners)} 个用户补齐默认商品，新增 {created_count} 个。", messages.SUCCESS)


@admin.register(UserInventory)
class UserInventoryAdmin(admin.ModelAdmin):
    list_display = ("id", "owner", "item", "item_kind", "quantity", "updated_at")
    list_filter = ("item__category", "item__item_kind", "item__rarity")
    search_fields = ("owner__username", "owner__email", "item__title", "item__catalog_key")
    raw_id_fields = ("owner", "item")
    readonly_fields = ("created_at", "updated_at")
    list_per_page = 50

    @admin.display(description="道具类型")
    def item_kind(self, obj):
        return obj.item.item_kind


@admin.register(RedemptionRecord)
class RedemptionRecordAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "owner",
        "item",
        "item_category",
        "item_kind",
        "cost_secondary",
        "status",
        "fulfilled_at",
        "rejected_at",
        "created_at",
    )
    list_filter = ("status", "item__category", "item__item_kind")
    search_fields = ("owner__username", "owner__email", "item__title", "item__catalog_key", "note")
    raw_id_fields = ("owner", "item", "transaction", "refund_transaction")
    readonly_fields = ("created_at", "updated_at", "effect_snapshot")
    list_per_page = 50
    formfield_overrides = {
        models.JSONField: {"widget": forms.Textarea(attrs={"rows": 8, "cols": 80})},
    }

    @admin.display(description="商品大类")
    def item_category(self, obj):
        return obj.item.category

    @admin.display(description="商品类型")
    def item_kind(self, obj):
        return obj.item.item_kind
