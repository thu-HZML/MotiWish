from django.contrib import admin

from apps.wallet.models import Wallet, WalletTransaction


@admin.register(Wallet)
class WalletAdmin(admin.ModelAdmin):
    list_display = ("id", "owner", "primary_balance", "secondary_balance", "updated_at")
    search_fields = ("owner__username", "owner__email")


@admin.register(WalletTransaction)
class WalletTransactionAdmin(admin.ModelAdmin):
    list_display = ("id", "owner", "currency_type", "reason", "delta", "balance_after", "created_at")
    list_filter = ("currency_type", "reason")
    search_fields = ("owner__username", "reference_id", "memo")
