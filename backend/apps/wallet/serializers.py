from drf_spectacular.utils import extend_schema_field
from rest_framework import serializers

from apps.wallet.models import Wallet, WalletTransaction


class WalletSerializer(serializers.ModelSerializer):
    primary_debt = serializers.IntegerField(read_only=True)
    is_in_debt = serializers.BooleanField(read_only=True)
    primary_debt_floor = serializers.SerializerMethodField()

    class Meta:
        model = Wallet
        fields = (
            "id",
            "primary_balance",
            "secondary_balance",
            "primary_debt",
            "is_in_debt",
            "primary_debt_floor",
            "created_at",
            "updated_at",
        )

    @extend_schema_field(serializers.IntegerField())
    def get_primary_debt_floor(self, obj):
        return Wallet.PRIMARY_DEBT_FLOOR


class WalletTransactionSerializer(serializers.ModelSerializer):
    class Meta:
        model = WalletTransaction
        fields = (
            "id",
            "currency_type",
            "reason",
            "delta",
            "balance_before",
            "balance_after",
            "reference_type",
            "reference_id",
            "memo",
            "payload",
            "created_at",
        )
