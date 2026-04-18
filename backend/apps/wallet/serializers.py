from rest_framework import serializers

from apps.wallet.models import Wallet, WalletTransaction


class WalletSerializer(serializers.ModelSerializer):
    class Meta:
        model = Wallet
        fields = ("id", "primary_balance", "secondary_balance", "created_at", "updated_at")


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
