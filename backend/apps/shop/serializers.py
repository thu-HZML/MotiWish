from rest_framework import serializers

from apps.shop.models import RedemptionRecord, WishItem


class WishItemSerializer(serializers.ModelSerializer):
    class Meta:
        model = WishItem
        fields = "__all__"
        read_only_fields = ("owner", "created_at", "updated_at")


class RedemptionRecordSerializer(serializers.ModelSerializer):
    item = WishItemSerializer(read_only=True)

    class Meta:
        model = RedemptionRecord
        fields = "__all__"
