from rest_framework import serializers

from apps.shop.models import (
    RedemptionRecord,
    ShopItemCategory,
    ShopItemRarity,
    UserInventory,
    WishItem,
    WishPriceTier,
)
from apps.shop.services import PRICE_BOUNDS


class WishItemSerializer(serializers.ModelSerializer):
    class Meta:
        model = WishItem
        fields = "__all__"
        read_only_fields = ("owner", "created_at", "updated_at")

    def validate(self, attrs):
        category = attrs.get("category", getattr(self.instance, "category", ShopItemCategory.WISH))
        price_tier = attrs.get("price_tier", getattr(self.instance, "price_tier", WishPriceTier.MEDIUM))
        price_secondary = attrs.get("price_secondary", getattr(self.instance, "price_secondary", None))
        effect_payload = attrs.get("effect_payload", getattr(self.instance, "effect_payload", {}))

        if price_secondary is not None:
            bounds = PRICE_BOUNDS[price_tier]
            if price_secondary < bounds["min"] or price_secondary > bounds["max"]:
                raise serializers.ValidationError(
                    {"price_secondary": f"{price_tier} 档位价格必须在 {bounds['min']} 到 {bounds['max']} 之间。"}
                )

        if category == ShopItemCategory.EXPERIENCE_PACK:
            if int(effect_payload.get("experience", 0)) <= 0:
                raise serializers.ValidationError({"effect_payload": "经验材料必须配置正数 experience。"})

        return attrs


class ShopMetaSerializer(serializers.Serializer):
    categories = serializers.JSONField()
    rarities = serializers.JSONField()
    tiers = serializers.JSONField()
    bounds = serializers.JSONField()


class WishPricingPreviewSerializer(serializers.Serializer):
    price_tier = serializers.ChoiceField(choices=WishPriceTier.choices)
    suggested_price = serializers.IntegerField(min_value=0)


class WishPricingPreviewPayloadSerializer(serializers.Serializer):
    price_tier = serializers.ChoiceField(choices=WishPriceTier.choices)
    requested_price = serializers.IntegerField()
    clamped_price = serializers.IntegerField()
    bounds = serializers.JSONField()


class RedemptionActionSerializer(serializers.Serializer):
    note = serializers.CharField(required=False, allow_blank=True, max_length=255)
    refund = serializers.BooleanField(required=False)


class RedemptionRecordSerializer(serializers.ModelSerializer):
    item = WishItemSerializer(read_only=True)

    class Meta:
        model = RedemptionRecord
        fields = "__all__"


class UserInventorySerializer(serializers.ModelSerializer):
    item = WishItemSerializer(read_only=True)

    class Meta:
        model = UserInventory
        fields = ("id", "item", "quantity", "created_at", "updated_at")


def build_shop_meta():
    return {
        "categories": [{"value": key, "label": label} for key, label in ShopItemCategory.choices],
        "rarities": [{"value": key, "label": label} for key, label in ShopItemRarity.choices],
        "tiers": [{"value": key, "label": label} for key, label in WishPriceTier.choices],
        "bounds": PRICE_BOUNDS,
    }